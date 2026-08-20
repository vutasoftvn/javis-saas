"""COSA Co-Founder API Router (F4 Specification).

Cung cấp các API endpoints tương tác chính giữa Human Founder và COSA Co-Founder:
- /chat: Hội thoại và chỉ đạo Co-Founder
- /pulse: Lấy nhịp tim tổng thể doanh nghiệp (Company Pulse)
- /top3: Lấy Top 3 Next Best Actions hôm nay
- /challenge: Kiểm tra phản biện giả định của Founder dựa trên Evidence
- /decisions: Quản lý hàng đợi quyết định chiến lược (Founder Decision Queue)
- /decisions/{id}/resolve: Chốt quyết định chiến lược
"""
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.auth import get_current_user
from app.core.workspace_context import WorkspaceContext, get_workspace_context, resolve_workspace_context
from app.platform.auth.models import User
from app.workforce.api.admin_api import AsyncSessionAdapter, get_workforce_db
from app.workforce.orchestrator.cosa_cofounder_service import (
    CosaCofounderService,
    CoFounderMessageResponse,
    CompanyPulseResponse,
    NextBestActionItem,
    ChallengeAnalysis,
)
from app.workforce.governance.founder_decision_service import FounderDecisionService
from app.workforce.schemas.decision_schemas import (
    FounderDecisionCreate,
    FounderDecisionResolveRequest,
    FounderDecisionResponse,
)


router = APIRouter(prefix="/cofounder", tags=["COSA Co-Founder"])


class CoFounderChatRequest(BaseModel):
    message: str = Field(..., description="Nội dung trao đổi hoặc câu hỏi từ Human Founder")
    workspace_id: Optional[int] = None
    project_id: Optional[int] = None


class ChallengeCheckRequest(BaseModel):
    statement: str = Field(..., description="Ý tưởng, tính năng hoặc giả định cần kiểm tra")
    evidence_summary: Optional[str] = None


@router.post("/chat", response_model=CoFounderMessageResponse)
async def chat_with_cofounder(
    req: CoFounderChatRequest,
    db=Depends(get_workforce_db),
    sync_db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Trò chuyện trực tiếp với COSA Co-Founder."""
    ctx: WorkspaceContext = resolve_workspace_context(sync_db, current_user, req.workspace_id)
    service = CosaCofounderService(db, sync_db=sync_db)
    response = await service.handle_founder_message(
        message=req.message,
        workspace_id=ctx.workspace_id,
        project_id=req.project_id,
        user_id=current_user.id if current_user else None,
    )
    return response


@router.post("/missions/{mission_id}/confirm", response_model=CoFounderMessageResponse)
async def confirm_mission(
    mission_id: int,
    db=Depends(get_workforce_db),
    sync_db: Session = Depends(get_db),
    ctx: WorkspaceContext = Depends(get_workspace_context),
):
    """Founder xác nhận chạy 1 Mission đang chờ (status=draft, risk > R1) —
    G2 §7.3 / G3 §12."""
    service = CosaCofounderService(db, sync_db=sync_db)
    try:
        return await service.confirm_mission(mission_id=mission_id, user_id=ctx.user_id, workspace_id=ctx.workspace_id)
    except PermissionError:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Mission does not belong to this workspace")
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.get("/pulse", response_model=CompanyPulseResponse)
async def get_company_pulse(
    project_id: Optional[int] = Query(None),
    db=Depends(get_workforce_db),
    ctx: WorkspaceContext = Depends(get_workspace_context),
):
    """Lấy thông tin nhịp tim doanh nghiệp (Company Pulse) cho Hologram Hub."""
    service = CosaCofounderService(db)
    pulse = await service.get_company_pulse(workspace_id=ctx.workspace_id, project_id=project_id)
    return pulse


@router.get("/top3", response_model=List[NextBestActionItem])
async def get_top3_focus(
    project_id: Optional[int] = Query(None),
    db=Depends(get_workforce_db),
    ctx: WorkspaceContext = Depends(get_workspace_context),
):
    """Lấy danh sách Top 3 hành động tốt nhất hôm nay (Next Best Action)."""
    service = CosaCofounderService(db)
    actions = await service.get_next_best_action(workspace_id=ctx.workspace_id, project_id=project_id)
    return actions


@router.post("/challenge", response_model=ChallengeAnalysis)
async def evaluate_challenge(
    req: ChallengeCheckRequest,
    db=Depends(get_workforce_db),
    current_user: User = Depends(get_current_user),
):
    """Kiểm tra phản biện giả định của Founder theo cơ chế Problem-First / Evidence-Driven."""
    service = CosaCofounderService(db)
    analysis = await service.challenge_assumptions(
        founder_input=req.statement,
        evidence_summary=req.evidence_summary,
    )
    return analysis


@router.get("/decisions", response_model=List[FounderDecisionResponse])
async def list_pending_decisions(
    project_id: Optional[int] = Query(None),
    limit: int = Query(50),
    db=Depends(get_workforce_db),
    ctx: WorkspaceContext = Depends(get_workspace_context),
):
    """Lấy danh sách các quyết định đang chờ Founder duyệt ('Waiting for You')."""
    service = FounderDecisionService(db)
    decisions = await service.list_pending_decisions(
        workspace_id=ctx.workspace_id,
        project_id=project_id,
        limit=limit,
    )
    return decisions


@router.post("/decisions", response_model=FounderDecisionResponse)
async def create_founder_decision(
    req: FounderDecisionCreate,
    db=Depends(get_workforce_db),
    sync_db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Tạo mới một bài toán quyết định chiến lược từ Co-Founder."""
    ctx: WorkspaceContext = resolve_workspace_context(sync_db, current_user, req.workspace_id)
    req.workspace_id = ctx.workspace_id
    service = FounderDecisionService(db)
    decision = await service.create_decision(req)
    return decision


@router.post("/decisions/{decision_id}/resolve", response_model=FounderDecisionResponse)
async def resolve_founder_decision(
    decision_id: int,
    req: FounderDecisionResolveRequest,
    db=Depends(get_workforce_db),
    ctx: WorkspaceContext = Depends(get_workspace_context),
):
    """Founder chốt quyết định chiến lược."""
    service = FounderDecisionService(db)
    resolved = await service.resolve_decision(
        decision_id=decision_id,
        resolve_data=req,
        user_id=ctx.user_id,
        workspace_id=ctx.workspace_id,
    )
    if not resolved:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Decision with ID {decision_id} not found",
        )
    return resolved
