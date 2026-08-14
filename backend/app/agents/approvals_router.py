from typing import Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.agents.governance.approval_service import ApprovalService
from app.core.auth import get_current_workspace_member
from app.db.models import WorkspaceMember
from app.db.session import get_db

router = APIRouter()


class ApprovalResponse(BaseModel):
    id: str
    workspace_id: str
    requested_by_agent: str
    action_type: str
    tool_name: str
    input_preview: Optional[dict[str, Any]] = None
    risk_level: str
    status: str
    requested_at: str
    expires_at: Optional[str] = None
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[str] = None
    reason: Optional[str] = None


class RejectRequest(BaseModel):
    reason: Optional[str] = None


def _to_response(approval) -> dict[str, Any]:
    return {
        "id": str(approval.id),
        "workspace_id": str(approval.workspace_id),
        "requested_by_agent": approval.requested_by_agent,
        "action_type": approval.action_type,
        "tool_name": approval.tool_name,
        "input_preview": approval.input_preview_jsonb or {},
        "risk_level": approval.risk_level,
        "status": approval.status,
        "requested_at": approval.requested_at.isoformat() if approval.requested_at else None,
        "expires_at": approval.expires_at.isoformat() if approval.expires_at else None,
        "reviewed_by": str(approval.reviewed_by) if approval.reviewed_by else None,
        "reviewed_at": approval.reviewed_at.isoformat() if approval.reviewed_at else None,
        "reason": approval.reason,
    }


@router.get("", response_model=list[dict[str, Any]])
def list_pending_approvals(
    db: Session = Depends(get_db),
    current_member: WorkspaceMember = Depends(get_current_workspace_member),
) -> list[dict[str, Any]]:
    """List all pending agent approvals in current workspace."""
    approvals = ApprovalService.list_pending(db, current_member.workspace_id)
    return [_to_response(appr) for appr in approvals]


@router.post("/{approval_id}/approve", response_model=dict[str, Any])
def approve_agent_action(
    approval_id: int,
    db: Session = Depends(get_db),
    current_member: WorkspaceMember = Depends(get_current_workspace_member),
) -> dict[str, Any]:
    """Approve a pending agent action."""
    try:
        approval = ApprovalService.approve(
            db=db,
            workspace_id=current_member.workspace_id,
            approval_id=approval_id,
            reviewed_by=current_member.user_id,
        )
        return _to_response(approval)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )


@router.post("/{approval_id}/reject", response_model=dict[str, Any])
def reject_agent_action(
    approval_id: int,
    payload: RejectRequest,
    db: Session = Depends(get_db),
    current_member: WorkspaceMember = Depends(get_current_workspace_member),
) -> dict[str, Any]:
    """Reject a pending agent action with an optional reason."""
    try:
        approval = ApprovalService.reject(
            db=db,
            workspace_id=current_member.workspace_id,
            approval_id=approval_id,
            reviewed_by=current_member.user_id,
            reason=payload.reason,
        )
        return _to_response(approval)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )
