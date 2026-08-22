"""Founder Decision Service (F4 Specification - Decision Engine).

Quản lý toàn bộ vòng đời của Founder Decisions:
- Tạo bài toán / câu hỏi chiến lược từ Co-Founder
- Đính kèm Evidence IDs (tích hợp F1/F3)
- Hàng đợi chờ quyết định của Founder (Waiting for You Queue)
- Cập nhật quyết định của Founder (Resolve Decision)
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy import select, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from workforce.models import FounderDecision
from workforce.schemas.decision_schemas import (
    FounderDecisionCreate,
    FounderDecisionResolveRequest,
    DecisionStatusEnum,
)
from core.snowflake import generate_snowflake_id


class FounderDecisionService:
    """Service quản trị các quyết định chiến lược của Founder."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_decision(
        self,
        payload: FounderDecisionCreate,
    ) -> FounderDecision:
        """Tạo một yêu cầu quyết định chiến lược mới từ Co-Founder."""
        decision = FounderDecision(
            id=generate_snowflake_id(),
            workspace_id=payload.workspace_id,
            project_id=payload.project_id,
            domain=payload.domain.value if hasattr(payload.domain, "value") else str(payload.domain),
            question=payload.question,
            context_summary=payload.context_summary,
            options_jsonb=[opt.model_dump() if hasattr(opt, "model_dump") else (opt.dict() if hasattr(opt, "dict") else opt) for opt in payload.options_jsonb],
            ai_recommendation_jsonb=payload.ai_recommendation_jsonb or {},
            evidence_ids=payload.evidence_ids or [],
            risk_analysis_jsonb=payload.risk_analysis_jsonb or {},
            status=DecisionStatusEnum.PENDING.value,
        )
        self.db.add(decision)
        await self.db.flush()
        return decision

    async def get_decision_by_id(
        self,
        decision_id: int,
        workspace_id: Optional[int] = None,
    ) -> Optional[FounderDecision]:
        """Lấy chi tiết một quyết định theo ID."""
        stmt = select(FounderDecision).where(FounderDecision.id == decision_id)
        if workspace_id is not None:
            stmt = stmt.where(FounderDecision.workspace_id == workspace_id)
        res = await self.db.execute(stmt)
        return res.scalars().first()

    async def list_pending_decisions(
        self,
        workspace_id: Optional[int] = None,
        project_id: Optional[int] = None,
        limit: int = 50,
    ) -> List[FounderDecision]:
        """Lấy danh sách các quyết định đang chờ Founder duyệt ('Waiting for You')."""
        stmt = select(FounderDecision).where(FounderDecision.status == DecisionStatusEnum.PENDING.value)
        if workspace_id is not None:
            stmt = stmt.where(FounderDecision.workspace_id == workspace_id)
        if project_id is not None:
            stmt = stmt.where(FounderDecision.project_id == project_id)
        stmt = stmt.order_by(desc(FounderDecision.created_at)).limit(limit)
        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    async def resolve_decision(
        self,
        decision_id: int,
        resolve_data: FounderDecisionResolveRequest,
        user_id: Optional[int] = None,
        workspace_id: Optional[int] = None,
    ) -> Optional[FounderDecision]:
        """Ghi nhận quyết định cuối cùng từ Founder."""
        decision = await self.get_decision_by_id(decision_id, workspace_id)
        if not decision:
            return None

        decision.decision_made = resolve_data.decision_made
        if resolve_data.founder_notes:
            decision.founder_notes = resolve_data.founder_notes
        decision.status = resolve_data.status.value if hasattr(resolve_data.status, "value") else str(resolve_data.status)
        decision.decided_by_user_id = user_id
        decision.decided_at = datetime.utcnow()
        await self.db.flush()
        return decision
