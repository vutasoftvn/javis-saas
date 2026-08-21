"""Outcome Observer, Rule-based Verifier, and Safe Learning Writer for COSA Agents."""

from datetime import datetime, timezone
import logging
from typing import Any, Optional

from sqlalchemy.orm import Session

from workforce.agents.learning.models import JobOutcome
from workforce.memory.models import AgentMemoryEntry
from workforce.memory.service import FiveLayerMemoryManager
from core.snowflake import generate_snowflake_id

logger = logging.getLogger(__name__)


class Verifier:
    """Evaluates whether actual execution outcome satisfies expected business metrics."""

    @classmethod
    def verify(cls, expected: dict[str, Any], actual: dict[str, Any]) -> bool:
        if not expected:
            return True

        for k, exp_val in expected.items():
            act_val = actual.get(k)
            if act_val is None:
                return False
            # If expected is a target number, check if actual meets or exceeds
            if isinstance(exp_val, (int, float)) and isinstance(act_val, (int, float)):
                if act_val < exp_val:
                    return False
            elif exp_val != act_val:
                return False
        return True


class LearningWriter:
    """Writes verified outcomes into long-term memory (`workforce.memory.AgentMemoryEntry`,
    L4_LEARNING) with provenance.

    G3 Phase 1E: previously wrote a separate `AgentMemoryItem`
    (`control_plane.models`, table `agent_business_memories`) - retired
    outright (zero production readers, this was its only writer) in favor of
    the canonical `workforce.memory` write path, per G2 §2.5.
    """

    @classmethod
    def record_learning(
        cls,
        db: Session,
        workspace_id: int,
        run_id: int,
        domain: str,
        metric: str,
        expected: dict[str, Any],
        actual: dict[str, Any],
        source_ref: Optional[str] = None,
    ) -> tuple[JobOutcome, Optional[AgentMemoryEntry]]:
        is_verified = Verifier.verify(expected, actual)

        outcome = JobOutcome(
            id=generate_snowflake_id(),
            workspace_id=workspace_id,
            run_id=run_id,
            metric=metric,
            expected_jsonb=expected,
            actual_jsonb=actual,
            verified=is_verified,
            source_ref=source_ref,
            created_at=datetime.now(timezone.utc),
        )
        db.add(outcome)
        db.commit()
        db.refresh(outcome)

        memory_entry: Optional[AgentMemoryEntry] = None
        # Rule: Learning is ONLY recorded into long-term memory when verified is True
        if is_verified:
            memory_entry = FiveLayerMemoryManager.store_memory(
                db=db,
                workspace_id=workspace_id,
                layer="L4_LEARNING",
                key=f"outcome:{metric}:{outcome.id}",
                value={
                    "metric": metric,
                    "actual": actual,
                    "expected": expected,
                    "source_ref": source_ref,
                },
                domain=domain,
                provenance={
                    "source": "verified_job_outcome",
                    "job_outcome_id": str(outcome.id),
                    "run_id": str(run_id),
                },
            )

        return outcome, memory_entry
