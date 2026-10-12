"""Dịch vụ wakeup (Dự án C): cổng kiểm tra, sổ cái, schedule. Org chart chỉ là đường leo
thang; không nới capability/autonomy của ai."""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, Literal
from uuid import UUID, uuid4

from agent.governance.contracts import AutonomyLevel
from agent.workforce.escalation import next_escalation_target
from agent.workforce.wakeup import WakeConfig, wakeup_enabled
from agent.workforce.wakeup_ledger import WakeupEntry, WakeupLedger

from apps.cosa.agents.agent_profile_specs import AGENT_PROFILE_SPECS

logger = logging.getLogger(__name__)

__all__ = [
    "MIN_WAKE_AUTONOMY",
    "WAKE_PROFILE_BY_FUNCTIONAL_KEY",
    "WakeOutcome",
    "WakeupService",
    "canonical_assignment_id",
    "evaluate_wake_target",
]

# Ánh xạ bảo thủ functional_key -> profile thực thi được. Vắng mặt = không thể đánh thức.
WAKE_PROFILE_BY_FUNCTIONAL_KEY: dict[str, str] = {
    "cashflow_planner": "finance",
    "accounting_document_specialist": "finance",
    "campaign_planner": "marketing",
    "founder_office_orchestrator": "operations",
}

MIN_WAKE_AUTONOMY = AutonomyLevel.L2
_ELIGIBILITY_REASONS = frozenset(
    {
        "assignment_not_found",
        "assignment_not_active",
        "employee_not_active",
        "no_executable_profile",
        "autonomy_below_minimum",
    }
)
_RANK = {"L0": 0, "L1": 1, "L2": 2, "L3": 3}


def canonical_assignment_id(value: str) -> str | None:
    """Dạng chuẩn (chữ thường, có gạch ngang) của UUID; None nếu không phải UUID."""
    try:
        return str(UUID(str(value)))
    except (ValueError, AttributeError, TypeError):
        return None


def _profile_autonomy(profile: str) -> str:
    spec = AGENT_PROFILE_SPECS.get(profile)
    return AutonomyLevel(spec.autonomy_level).value if spec is not None else "L0"


@dataclass(frozen=True)
class WakeOutcome:
    status: Literal["scheduled", "duplicate", "suppressed", "operator"]
    reason: str | None = None
    assignment_id: str | None = None


async def evaluate_wake_target(
    workforce_repo: Any, workspace_id: str, assignment_id: str
) -> tuple[str | None, str | None]:
    """(profile, None) nếu đánh thức được; ngược lại (None, lý do)."""
    canonical = canonical_assignment_id(assignment_id)
    if canonical is None:
        return None, "invalid_assignment_id"
    assignment_id = canonical
    assignment = await workforce_repo.get_assignment(workspace_id, assignment_id)
    if assignment is None:
        return None, "assignment_not_found"
    if assignment.status != "ACTIVE":
        return None, "assignment_not_active"
    if assignment.agent_instance_id is not None:
        employee = await workforce_repo.get_employee(workspace_id, assignment.agent_instance_id)
        if employee is None or employee.status != "ACTIVE":
            return None, "employee_not_active"
    profile = WAKE_PROFILE_BY_FUNCTIONAL_KEY.get(assignment.functional_key)
    if profile is None or profile not in AGENT_PROFILE_SPECS:
        return None, "no_executable_profile"
    if _RANK[_profile_autonomy(profile)] < _RANK[MIN_WAKE_AUTONOMY.value]:
        return None, "autonomy_below_minimum"
    return profile, None


class WakeupService:
    def __init__(
        self,
        *,
        workforce_repo: Any,
        ledger: WakeupLedger,
        scheduler: Any,
        config: WakeConfig | None = None,
        now: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self._repo = workforce_repo
        self._ledger = ledger
        self._scheduler = scheduler
        self._config = config
        self._now = now

    async def request_wakeup(
        self,
        *,
        workspace_id: str,
        assignment_id: str,
        project_id: str,
        reason_kind: str,
        source_ref: str,
        hop: int = 0,
    ) -> WakeOutcome:
        if not wakeup_enabled():
            return WakeOutcome("suppressed", "flag_off")
        config = self._config or WakeConfig.from_env()
        canonical = canonical_assignment_id(assignment_id)
        if canonical is None:
            return WakeOutcome("suppressed", "invalid_assignment_id")
        assignment_id = canonical
        profile, reason = await evaluate_wake_target(self._repo, workspace_id, assignment_id)
        if profile is None:
            return WakeOutcome("suppressed", reason)
        if hop > config.hop_cap:
            return WakeOutcome("suppressed", "hop_cap_reached")
        now = self._now()
        recent = await self._ledger.count_since(
            workspace_id, assignment_id, now - timedelta(hours=24)
        )
        if recent >= config.max_per_day:
            return WakeOutcome("suppressed", "rate_cap")
        # count_since -> record_if_absent là soft cap: chấp nhận vượt nhẹ khi đồng thời.
        entry = WakeupEntry(
            wake_id=uuid4().hex,
            workspace_id=workspace_id,
            assignment_id=assignment_id,
            project_id=project_id,
            reason_kind=reason_kind,
            source_ref=source_ref,
            hop=hop,
            created_at=now,
        )
        if not await self._ledger.record_if_absent(entry):
            return WakeOutcome("duplicate", assignment_id=assignment_id)
        try:
            await self._scheduler.schedule(
                target_spec_id=AGENT_PROFILE_SPECS[profile].id,
                input_payload={
                    "task_type": "agent_wakeup",
                    "workspace_id": workspace_id,
                    "assignment_id": assignment_id,
                    "project_id": project_id,
                },
                coalescing_key=f"wake:{workspace_id}:{assignment_id}:{project_id}",
                run_at=now + timedelta(seconds=config.debounce_sec),
            )
        except Exception as exc:
            logger.warning("wakeup schedule failed: %s", type(exc).__name__)
            # Hàng sổ cái vẫn UNHANDLED: lần wakeup kế tiếp của cùng (assignment, project)
            # sẽ nhặt nó vì handler đọc list_unhandled.
            return WakeOutcome("suppressed", "schedule_failed", assignment_id=assignment_id)
        return WakeOutcome("scheduled", assignment_id=assignment_id)

    async def escalate(
        self,
        *,
        workspace_id: str,
        from_assignment_id: str,
        project_id: str,
        reason_kind: str,
        source_ref: str,
        hop: int = 0,
    ) -> WakeOutcome:
        if not wakeup_enabled():
            return WakeOutcome("suppressed", "flag_off")
        config = self._config or WakeConfig.from_env()
        canonical = canonical_assignment_id(from_assignment_id)
        if canonical is None:
            return WakeOutcome("suppressed", "invalid_assignment_id")
        current = UUID(canonical)
        records = await self._repo.list_assignments(workspace_id)
        nodes: dict[UUID, tuple[UUID | None, str]] = {
            r.assignment_id: (r.reports_to_assignment_id, r.status) for r in records
        }
        while True:
            target = next_escalation_target(
                nodes=nodes, assignment_id=current, hop=hop, hop_cap=config.hop_cap
            )
            if target.kind == "operator" or target.assignment_id is None:
                return WakeOutcome("operator", target.reason)
            outcome = await self.request_wakeup(
                workspace_id=workspace_id,
                assignment_id=str(target.assignment_id),
                project_id=project_id,
                reason_kind=reason_kind,
                source_ref=source_ref,
                hop=target.hop,
            )
            if outcome.status == "suppressed" and outcome.reason in _ELIGIBILITY_REASONS:
                # Quản lý không đánh thức được: chỉ đi tiếp lên quản lý kế, không nới gì.
                # Vòng lặp bị chặn bởi hop_cap vì mỗi bước tăng hop.
                logger.info(
                    "wakeup escalate skipped manager ws=%s assignment=%s reason=%s",
                    workspace_id,
                    target.assignment_id,
                    outcome.reason,
                )
                current, hop = target.assignment_id, target.hop
                continue
            return outcome
