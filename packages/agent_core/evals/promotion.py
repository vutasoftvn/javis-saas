from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field

from agent_core.evals.artifacts import EvalRun
from agent_core.governance.contracts import PinnedSpecIdentity, SpecDependencyEdge

__all__ = ["PromotionEvidence", "build_promotion_evidence"]


class PromotionEvidence(BaseModel):
    """Bằng chứng bất biến cho quyết định promotion — Wave M4, theo
    COSA_MARIN_PATTERNS_INTEGRATION_AND_ADJUSTMENT_PLAN_2026-08-26.md §12.2.
    `agent_core` CHỈ tạo evidence này, KHÔNG tự quyết promote —
    PromotionDecision (quyền activate production) thuộc `services/cosa`, xem
    docs/implementation/M4_PROMOTION_CONTROL_PLANE_BOUNDARY.md."""

    evidence_id: str = Field(default_factory=lambda: f"promoevid_{uuid.uuid4().hex[:12]}")
    target_ref: PinnedSpecIdentity
    required_eval_run_ids: list[str] = Field(default_factory=list)
    observed_fingerprints: dict[str, str] = Field(default_factory=dict)
    policy_version: str
    policy_checks_passed: bool
    check_details: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    def is_stale(self, current_fingerprints: dict[str, str]) -> bool:
        """True nếu bất kỳ fingerprint nào (target hoặc dependency) đã quan
        sát tại thời điểm tạo evidence KHÔNG còn khớp fingerprint hiện tại —
        nghĩa là artifact đã đổi sau khi eval pass, evidence không còn tin
        cậy được cho quyết định promote (§12.2 pseudo-invariant
        `evaluated_fingerprint == current_candidate_fingerprint`)."""
        for name, observed_hash in self.observed_fingerprints.items():
            if current_fingerprints.get(name) != observed_hash:
                return True
        return False


def build_promotion_evidence(
    *,
    target_ref: PinnedSpecIdentity,
    dependency_edges: tuple[SpecDependencyEdge, ...] = (),
    eval_runs: list[EvalRun],
    policy_version: str,
    pass_rate_threshold: float,
) -> PromotionEvidence:
    """Nối AgentSpecResolution.edges (Wave M2, SpecResolver.resolve_agent_spec_
    dependencies) + danh sách EvalRun đã chạy (Wave M3) thành 1
    PromotionEvidence. `policy_checks_passed` = True chỉ khi CÓ ít nhất 1
    eval_run VÀ toàn bộ đều status="completed" với pass_rate đạt ngưỡng —
    không có eval run nào KHÔNG được coi là "đã kiểm tra"."""
    observed_fingerprints: dict[str, str] = {target_ref.spec_id: target_ref.definition_hash}
    for edge in dependency_edges:
        observed_fingerprints[edge.dependency.spec_id] = edge.dependency.definition_hash

    policy_checks_passed = bool(eval_runs) and all(
        run.status == "completed" and (run.pass_rate or 0.0) >= pass_rate_threshold
        for run in eval_runs
    )
    check_details: dict[str, Any] = {
        "pass_rate_threshold": pass_rate_threshold,
        "eval_run_statuses": {run.run_id: run.status for run in eval_runs},
        "eval_run_pass_rates": {run.run_id: run.pass_rate for run in eval_runs},
    }

    return PromotionEvidence(
        target_ref=target_ref,
        required_eval_run_ids=[run.run_id for run in eval_runs],
        observed_fingerprints=observed_fingerprints,
        policy_version=policy_version,
        policy_checks_passed=policy_checks_passed,
        check_details=check_details,
    )
