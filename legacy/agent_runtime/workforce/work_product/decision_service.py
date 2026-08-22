from typing import List, Dict, Any, Optional
from datetime import datetime
from sqlalchemy import select, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from workforce.models import DecisionRecord
from core.snowflake import generate_snowflake_id


class DecisionRecordService:
    """Quản lý hồ sơ quyết định kiến trúc / chiến lược (ADR - Decision Records)."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_decision_record(
        self,
        title: str,
        context_summary: str,
        decision_content: str,
        consequences: Optional[str] = None,
        alternatives_considered: Optional[str] = None,
        author_agent_key: str = "founder_copilot",
        work_product_id: Optional[int] = None,
        task_id: Optional[int] = None,
        workspace_id: Optional[int] = None,
        status: str = "PROPOSED",
    ) -> DecisionRecord:
        dr = DecisionRecord(
            id=generate_snowflake_id(),
            workspace_id=workspace_id,
            work_product_id=work_product_id,
            task_id=task_id,
            title=title,
            status=status,
            context_summary=context_summary,
            decision_content=decision_content,
            consequences=consequences,
            alternatives_considered=alternatives_considered,
            author_agent_key=author_agent_key,
            created_at=datetime.utcnow(),
        )
        self.db.add(dr)
        await self.db.flush()
        return dr

    async def list_decisions(
        self,
        workspace_id: Optional[int] = None,
        status: Optional[str] = None,
    ) -> List[DecisionRecord]:
        stmt = select(DecisionRecord).order_by(desc(DecisionRecord.created_at))
        filters = []
        if workspace_id is not None:
            filters.append(DecisionRecord.workspace_id == workspace_id)
        if status:
            filters.append(DecisionRecord.status == status)
        if filters:
            stmt = stmt.where(and_(*filters))
        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    async def accept_decision(self, decision_id: int, user_id: int) -> DecisionRecord:
        stmt = select(DecisionRecord).where(DecisionRecord.id == decision_id)
        res = await self.db.execute(stmt)
        dr = res.scalars().first()
        if not dr:
            raise ValueError(f"DecisionRecord with ID {decision_id} not found")

        dr.status = "ACCEPTED"
        dr.approved_by_user_id = user_id
        await self.db.flush()
        return dr
