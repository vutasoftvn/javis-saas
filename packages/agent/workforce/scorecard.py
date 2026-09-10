"""Evidence-derived scorecard cho AI employee (Task 6, spec §12).

Scorecard CHỈ tính result đã manager/founder review — completed run một mình
không tạo business score. Tách theo agent_instance_id, assignment, spec hash,
skill version, outcome type, analysis depth, package type, time window.

Company attempt/review là nguồn sự thật (qua `CompanyEvidenceSource`); nếu
không lấy được -> trả `unavailable` kèm lý do, KHÔNG trả 0 (spec §12: "If
Company evidence is unavailable return unavailable with source reason, not
zero").
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol


@dataclass(frozen=True)
class ReviewedAttemptOutcome:
    agent_instance_id: str
    spec_hash: str
    outcome_type: str
    package_type: str
    review_decision: str  # ACCEPT | REWORK | REJECT
    review_latency_seconds: float | None = None
    retry_count: int = 0
    escalated: bool = False


class CompanyEvidenceSource(Protocol):
    async def reviewed_attempt_outcomes(
        self,
        workspace_id: str,
        agent_instance_id: str,
        window_start: datetime,
        window_end: datetime,
    ) -> list[ReviewedAttemptOutcome] | None:
        """None => Company evidence không lấy được (timeout/permiss)."""
        ...


@dataclass(frozen=True)
class EmployeeScorecard:
    workspace_id: str
    agent_instance_id: str
    window_start: datetime
    window_end: datetime
    available: bool = True
    unavailable_reason: str | None = None
    accepted_count: int = 0
    rework_count: int = 0
    reject_count: int = 0
    escalation_count: int = 0
    retry_count: int = 0
    accepted_by_spec: dict[str, int] = field(default_factory=dict)

    @classmethod
    def unavailable(
        cls,
        workspace_id: str,
        agent_instance_id: str,
        window_start: datetime,
        window_end: datetime,
        reason: str,
    ) -> EmployeeScorecard:
        return cls(
            workspace_id=workspace_id,
            agent_instance_id=agent_instance_id,
            window_start=window_start,
            window_end=window_end,
            available=False,
            unavailable_reason=reason,
        )


async def get_employee_scorecard(
    *,
    evidence: CompanyEvidenceSource,
    workspace_id: str,
    agent_instance_id: str,
    window_start: datetime,
    window_end: datetime,
) -> EmployeeScorecard:
    try:
        outcomes = await evidence.reviewed_attempt_outcomes(
            workspace_id, agent_instance_id, window_start, window_end
        )
    except Exception as exc:
        return EmployeeScorecard.unavailable(
            workspace_id, agent_instance_id, window_start, window_end, f"evidence_error:{exc}"
        )

    if outcomes is None:
        return EmployeeScorecard.unavailable(
            workspace_id,
            agent_instance_id,
            window_start,
            window_end,
            "company_evidence_unavailable",
        )

    accepted = rework = reject = escalations = retries = 0
    accepted_by_spec: dict[str, int] = {}
    for o in outcomes:
        retries += o.retry_count
        if o.escalated:
            escalations += 1
        if o.review_decision == "ACCEPT":
            accepted += 1
            accepted_by_spec[o.spec_hash] = accepted_by_spec.get(o.spec_hash, 0) + 1
        elif o.review_decision == "REWORK":
            rework += 1
        elif o.review_decision == "REJECT":
            reject += 1

    return EmployeeScorecard(
        workspace_id=workspace_id,
        agent_instance_id=agent_instance_id,
        window_start=window_start,
        window_end=window_end,
        available=True,
        accepted_count=accepted,
        rework_count=rework,
        reject_count=reject,
        escalation_count=escalations,
        retry_count=retries,
        accepted_by_spec=accepted_by_spec,
    )
