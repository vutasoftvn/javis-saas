from __future__ import annotations

from typing import Any

from agentos.core.approval import ApprovalService, ApprovalStatus
from agentos.core.policy import PermissionClass, PolicyDecision, PolicyEngine
from agentos.workflows.models import StepOutcome, StepStatus


class ApprovalGateStep:
    """Human approval node (blueprint §47 example: ...→Human Approval→...).
    Consults the PolicyEngine first: ALLOW passes straight through, DENY
    fails the step outright, REQUIRE_APPROVAL creates a pending Approval
    and pauses the workflow. Resuming a paused workflow re-checks the same
    approval via check_pending() rather than re-evaluating the policy —
    the decision to require approval, once made, doesn't get re-litigated.
    """

    def __init__(
        self,
        name: str,
        *,
        policy_engine: PolicyEngine,
        approval_service: ApprovalService,
        permission: PermissionClass,
        action: str,
        subject_key: str,
        requester: str,
    ) -> None:
        self.name = name
        self._policy_engine = policy_engine
        self._approval_service = approval_service
        self._permission = permission
        self._action = action
        self._subject_key = subject_key
        self._requester = requester

    async def run(self, state: dict[str, Any]) -> StepOutcome:
        decision = self._policy_engine.evaluate(self._permission)
        if decision == PolicyDecision.ALLOW:
            return StepOutcome(status=StepStatus.COMPLETED)
        if decision == PolicyDecision.DENY:
            return StepOutcome(status=StepStatus.FAILED, error=f"{self._permission.value} is denied by policy")

        approval = self._approval_service.request_approval(
            action=self._action, subject=state[self._subject_key], requester=self._requester
        )
        return StepOutcome(status=StepStatus.WAITING_APPROVAL, approval_id=approval.id)

    def check_pending(self, approval_id: str) -> StepOutcome:
        approval = self._approval_service.get(approval_id)
        if approval.status == ApprovalStatus.PENDING:
            return StepOutcome(status=StepStatus.WAITING_APPROVAL, approval_id=approval_id)
        if approval.status == ApprovalStatus.DENIED:
            return StepOutcome(
                status=StepStatus.FAILED, error=f"approval {approval_id} was denied: {approval.reason}"
            )
        return StepOutcome(status=StepStatus.COMPLETED)
