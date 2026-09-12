from __future__ import annotations

import hashlib
from typing import Any

from agent.runs.models import ApprovalSubject
from agent.workflows.models import StepOutcome, StepStatus

__all__ = ["ApprovalGateStep"]


class ApprovalGateStep:
    """Human approval node trong Workflow.

    Tạo CHANGE_REQUEST qua DurableApprovalService. Đánh giá Policy trước (nếu có):
    ALLOW đi thẳng tiếp, DENY fail ngay, REQUIRE_APPROVAL tạo change approval request
    với exact hash-binding và tạm dừng workflow.
    Khi resume, re-check approval qua check_pending(approval_id) bất đồng bộ.
    """

    def __init__(
        self,
        name: str,
        *,
        approval_service: Any,
        action: str = "",
        subject_key: str = "",
        subject_hash_key: str | None = None,
        policy_engine: Any = None,
        permission: Any = None,
        requester: str = "workflow_engine",
    ) -> None:
        self.name = name
        self._approval_service = approval_service
        self._action = action or name
        self._subject_key = subject_key or "subject"
        self._subject_hash_key = subject_hash_key
        self._policy_engine = policy_engine
        self._permission = permission
        self._requester = requester

    async def run(self, state: dict[str, Any]) -> StepOutcome:
        # 1. Evaluate policy if policy_engine configured
        if self._policy_engine is not None:
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

        # 2. Require trusted workspace_id
        workspace_id = state.get("workspace_id")
        if not workspace_id:
            return StepOutcome(
                status=StepStatus.FAILED,
                error="ApprovalGateStep requires trusted 'workspace_id' in state",
            )

        # 3. Require non-empty subject_key
        subject_val = state.get(self._subject_key)
        if not subject_val:
            return StepOutcome(
                status=StepStatus.FAILED,
                error=f"ApprovalGateStep requires non-empty subject key '{self._subject_key}' in state",
            )

        # 4. Determine subject definition hash and ref
        if self._subject_hash_key and state.get(self._subject_hash_key):
            def_hash = state[self._subject_hash_key]
        else:
            wf_instance_id = state.get("_workflow_instance_id", "wf_instance")
            wf_def_hash = state.get("_workflow_definition_hash", "wf_def")
            step_id = state.get("_workflow_step_id", self.name)
            def_hash = f"sha256:{hashlib.sha256(f'{wf_def_hash}:{step_id}:{subject_val}'.encode()).hexdigest()}"

        step_id = state.get("_workflow_step_id", self.name)
        wf_instance_id = state.get("_workflow_instance_id", "wf_instance")
        subject_ref = f"{wf_instance_id}:{step_id}"

        subject = ApprovalSubject(
            kind="workflow_gate",
            ref=subject_ref,
            definition_hash=def_hash,
        )

        record, _ = await self._approval_service.create_change_approval_request(
            workspace_id=workspace_id,
            project_id=state.get("project_id"),
            action=self._action,
            subject=subject,
            requirement={"role": "operator"},
            requester=self._requester,
        )

        return StepOutcome(
            status=StepStatus.WAITING_APPROVAL,
            approval_id=record.approval_id,
        )

    async def check_pending(self, approval_id: str, workspace_id: str | None = None) -> StepOutcome:
        approval = await self._approval_service.get_approval(approval_id)
        if not approval:
            return StepOutcome(status=StepStatus.FAILED, error=f"approval {approval_id} not found")

        status_val = approval.status.lower()
        if status_val == "pending":
            return StepOutcome(status=StepStatus.WAITING_APPROVAL, approval_id=approval_id)
        if status_val == "approved":
            return StepOutcome(status=StepStatus.COMPLETED)
        if status_val in ("denied", "rejected"):
            reason = approval.reason or "denied"
            return StepOutcome(
                status=StepStatus.FAILED,
                error=f"approval {approval_id} was denied: {reason}",
            )
        return StepOutcome(
            status=StepStatus.FAILED,
            error=f"approval {approval_id} in unexpected status: {approval.status}",
        )
