from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.auth import get_current_workspace_member
from app.core.feature_flags import require_flag, FLAG_NEXT_BEST_ACTION_V12
from app.db.models import WorkspaceMember
from app.founder_os.strategy.next_best_action_service import NextBestActionService

router = APIRouter()


class NextActionEvaluateRequest(BaseModel):
    project_id: Optional[int] = None
    portfolio_id: Optional[int] = None


class NextActionStatusUpdate(BaseModel):
    status: str  # proposed, accepted, dismissed, executed


@router.get("/ceo/next-actions")
def get_ceo_next_actions(
    workspace_id: int,
    limit: int = 5,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    """Lấy danh sách Top Next Best Actions cho màn hình CEO Brief / Hologram (Spec §37 & V12.6)."""
    require_flag(db, FLAG_NEXT_BEST_ACTION_V12, workspace_id)
    service = NextBestActionService(db, workspace_id, member.user_id)
    return {"next_actions": service.get_top_next_actions(limit=limit)}


@router.post("/ceo/next-actions/evaluate")
def evaluate_ceo_next_actions(
    workspace_id: int,
    data: Optional[NextActionEvaluateRequest] = None,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    """Tính toán và xếp hạng lại danh sách Next Best Actions (R0 Formula & R2 AI Rerank)."""
    require_flag(db, FLAG_NEXT_BEST_ACTION_V12, workspace_id)
    service = NextBestActionService(db, workspace_id, member.user_id)
    proj_id = data.project_id if data else None
    port_id = data.portfolio_id if data else None
    return {"rankings": service.evaluate_and_rank(project_id=proj_id, portfolio_id=port_id)}


@router.put("/ceo/next-actions/{action_id}/status")
def update_next_action_status(
    action_id: int,
    workspace_id: int,
    data: NextActionStatusUpdate,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    """Cập nhật trạng thái xử lý hành động (Accepted / Dismissed / Executed)."""
    require_flag(db, FLAG_NEXT_BEST_ACTION_V12, workspace_id)
    service = NextBestActionService(db, workspace_id, member.user_id)
    return service.update_action_status(action_id, data.status)
