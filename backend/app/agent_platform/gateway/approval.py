from typing import Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime

from app.agent_platform.identity.context import ExecutionContext
from app.core.snowflake import generate_snowflake_id


@dataclass
class ApprovalTicket:
    id: int
    workspace_id: int
    agent_id: int
    agent_key: str
    tool_key: str
    args: Dict[str, Any]
    risk_level: int
    reason: str
    status: str  # 'pending', 'approved', 'rejected'
    created_at: datetime


class ApprovalService:
    """Service xử lý quy trình Human-in-the-loop Approval khi hành động có rủi ro R3/R4."""

    def __init__(self):
        # Có thể tích hợp với DB PendingApproval / Outbox hiện có
        pass

    async def create_approval_request(
        self,
        context: ExecutionContext,
        tool_key: str,
        args: Dict[str, Any],
        risk_level: int,
        reason: str
    ) -> ApprovalTicket:
        ticket = ApprovalTicket(
            id=generate_snowflake_id(),
            workspace_id=context.workspace_id,
            agent_id=context.agent_id,
            agent_key=context.agent_key,
            tool_key=tool_key,
            args=args,
            risk_level=risk_level,
            reason=reason,
            status="pending",
            created_at=datetime.utcnow(),
        )
        return ticket
