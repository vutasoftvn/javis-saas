from __future__ import annotations

from typing import Any

from agent_core.contracts.wait import WaitDescriptor, WaitKind
from agent_core.runs.models import RunApprovalRecord
from agent_core.runs.repository import RunRepository

__all__ = ["ApprovalGateCoordinator"]


class ApprovalGateCoordinator:
    """Primitive điều phối phê duyệt con người và quản lý trạng thái chờ trong quá trình phối hợp."""

    def __init__(self, repository: RunRepository) -> None:
        self._repo = repository

    async def create_interruption(
        self,
        run_id: str,
        tool_call_id: str,
        checkpoint_ref: str,
        action: str,
        subject: str,
        requirement: dict[str, Any] | None = None,
        requester: str = "coordinator",
    ) -> WaitDescriptor:
        approval_id = f"appr_{run_id}_{tool_call_id}"
        record = RunApprovalRecord(
            approval_id=approval_id,
            run_id=run_id,
            tool_call_id=tool_call_id,
            checkpoint_ref=checkpoint_ref,
            status="pending",
            action=action,
            subject=subject,
            requirement=requirement or {},
            requester=requester,
        )
        await self._repo.create_approval(record)

        return WaitDescriptor(
            kind=WaitKind.APPROVAL,
            reason=f"Action '{action}' requires approval: {subject}",
            checkpoint_ref=checkpoint_ref,
            related_ref=approval_id,
        )

    async def check_approval_status(self, approval_id: str) -> str:
        approval = await self._repo.get_approval(approval_id)
        if not approval:
            return "not_found"
        return approval.status
