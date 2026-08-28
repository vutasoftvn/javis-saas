from __future__ import annotations

from typing import Any

from agent_core.workflows.models import StepOutcome, StepStatus

__all__ = ["ApprovalGateStep"]


class ApprovalGateStep:
    """Human approval node trong Workflow.

    Đánh giá Policy trước: ALLOW đi thẳng tiếp, DENY fail ngay, REQUIRE_APPROVAL
    tạo pending approval và tạm dừng workflow. Khi resume, re-check approval
    qua check_pending() thay vì re-evaluate từ đầu.
    """

    def __init__(
        self,
        name: str,
        *,
        policy_engine: Any,
        approval_service: Any,
        permission: Any = None,
        action: str = "",
        subject_key: str = "",
        requester: str = "workflow_engine",
    ) -> None:
        self.name = name
        self._policy_engine = policy_engine
        self._approval_service = approval_service
        self._permission = permission
        self._action = action
        self._subject_key = subject_key
        self._requester = requester

    async def run(self, state: dict[str, Any]) -> StepOutcome:
        # Gọi policy_engine.evaluate hoặc evaluate_access
        if hasattr(self._policy_engine, "evaluate"):
            decision = self._policy_engine.evaluate(self._permission)
        elif hasattr(self._policy_engine, "evaluate_access"):
            decision = self._policy_engine.evaluate_access(permission_class=self._permission)
        else:
            decision = "REQUIRE_APPROVAL"

        decision_str = str(
            getattr(decision, "value", getattr(decision, "outcome", decision))
        ).upper()
        if "ALLOW" in decision_str:
            return StepOutcome(status=StepStatus.COMPLETED)
        if "DENY" in decision_str:
            perm_val = getattr(self._permission, "value", self._permission)
            return StepOutcome(status=StepStatus.FAILED, error=f"{perm_val} is denied by policy")

        subject_val = state.get(self._subject_key, "")
        approval = self._approval_service.request_approval(
            action=self._action, subject=subject_val, requester=self._requester
        )
        return StepOutcome(
            status=StepStatus.WAITING_APPROVAL, approval_id=getattr(approval, "id", str(approval))
        )

    def check_pending(self, approval_id: str) -> StepOutcome:
        approval = self._approval_service.get(approval_id)
        status_val = str(getattr(approval, "status", "")).upper()
        if "PENDING" in status_val or "WAITING" in status_val:
            return StepOutcome(status=StepStatus.WAITING_APPROVAL, approval_id=approval_id)
        if "DENIED" in status_val or "REJECTED" in status_val:
            reason = getattr(approval, "reason", "denied")
            return StepOutcome(
                status=StepStatus.FAILED, error=f"approval {approval_id} was denied: {reason}"
            )
        return StepOutcome(status=StepStatus.COMPLETED)
