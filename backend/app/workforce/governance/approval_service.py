from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy import select, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.workforce.models import ApprovalRequest
from app.workforce.governance.risk_evaluator import RiskEvaluation
from app.core.snowflake import generate_snowflake_id


class ApprovalInboxService:
    """Service quản lý Human Approval Inbox dành cho Founder và Team Leads."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_request(
        self,
        requester_agent_key: str,
        action_type: str,
        risk_evaluation: RiskEvaluation,
        payload: Dict[str, Any],
        task_id: Optional[int] = None,
        run_id: Optional[int] = None,
        requester_agent_id: Optional[int] = None,
        tool_key: Optional[str] = None,
        workspace_id: Optional[int] = None,
    ) -> ApprovalRequest:
        ticket = ApprovalRequest(
            id=generate_snowflake_id(),
            workspace_id=workspace_id,
            task_id=task_id,
            run_id=run_id,
            requester_agent_id=requester_agent_id,
            requester_agent_key=requester_agent_key,
            action_type=action_type,
            risk_level=risk_evaluation.tier.value,
            required_role=risk_evaluation.required_role,
            status="PENDING",
            tool_key=tool_key,
            payload_jsonb=payload,
            reason=risk_evaluation.reason,
        )
        self.db.add(ticket)
        await self.db.flush()
        return ticket

    async def list_pending_requests(
        self,
        workspace_id: Optional[int] = None,
        required_role: Optional[str] = None,
    ) -> List[ApprovalRequest]:
        stmt = select(ApprovalRequest).where(ApprovalRequest.status == "PENDING").order_by(desc(ApprovalRequest.created_at))
        filters = []
        if workspace_id is not None:
            filters.append(ApprovalRequest.workspace_id == workspace_id)
        if required_role:
            filters.append(ApprovalRequest.required_role == required_role)
        if filters:
            stmt = stmt.where(and_(*filters))
        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    async def approve(
        self,
        request_id: int,
        approver_user_id: int,
        comment: Optional[str] = None,
    ) -> ApprovalRequest:
        stmt = select(ApprovalRequest).where(ApprovalRequest.id == request_id)
        res = await self.db.execute(stmt)
        req = res.scalars().first()
        if not req:
            raise ValueError(f"Approval request {request_id} not found")

        req.status = "APPROVED"
        req.approver_user_id = approver_user_id
        req.approver_comment = comment or "Approved by manager"
        req.approved_at = datetime.utcnow()
        await self.db.flush()
        return req

    async def reject(
        self,
        request_id: int,
        approver_user_id: int,
        reason: str,
    ) -> ApprovalRequest:
        stmt = select(ApprovalRequest).where(ApprovalRequest.id == request_id)
        res = await self.db.execute(stmt)
        req = res.scalars().first()
        if not req:
            raise ValueError(f"Approval request {request_id} not found")

        req.status = "REJECTED"
        req.approver_user_id = approver_user_id
        req.approver_comment = reason
        req.approved_at = datetime.utcnow()
        await self.db.flush()
        return req

    async def request_revision(
        self,
        request_id: int,
        approver_user_id: int,
        feedback: str,
    ) -> ApprovalRequest:
        stmt = select(ApprovalRequest).where(ApprovalRequest.id == request_id)
        res = await self.db.execute(stmt)
        req = res.scalars().first()
        if not req:
            raise ValueError(f"Approval request {request_id} not found")

        req.status = "REVISION_REQUESTED"
        req.approver_user_id = approver_user_id
        req.approver_comment = feedback
        req.approved_at = datetime.utcnow()
        await self.db.flush()
        return req

