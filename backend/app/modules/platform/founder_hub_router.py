from fastapi import APIRouter, Depends, HTTPException, status, Query, Body
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field

from app.db.session import get_db
from app.core.auth import get_current_workspace_member
from app.db.models import WorkspaceMember
from app.modules.platform.founder_hub_service import (
    get_founder_command_center_data,
    execute_quick_approval,
)

router = APIRouter()


class QuickApprovalRequest(BaseModel):
    approval_id: str = Field(..., description="ID của tác vụ hoặc phê duyệt (Snowflake String ID)")
    decision: str = Field(..., description="'approve' hoặc 'reject'")
    reason: Optional[str] = Field(None, description="Lý do phê duyệt hoặc từ chối")


@router.get("/workspaces/{workspace_id}/hub/command-center")
def get_command_center(
    workspace_id: int,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    """Lấy toàn bộ dữ liệu tổng hợp cho CEO Command Center."""
    if member.workspace_id != workspace_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: member does not belong to this workspace",
        )

    data = get_founder_command_center_data(
        db=db,
        workspace_id=workspace_id,
        user_id=member.user_id,
    )
    return {
        "status": "success",
        "data": data,
    }


@router.post("/workspaces/{workspace_id}/hub/quick-approve")
def quick_approve(
    workspace_id: int,
    payload: QuickApprovalRequest,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    """Xử lý phê duyệt nhanh cho Founder, cập nhật DB và đẩy Outbox queue."""
    if member.workspace_id != workspace_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: member does not belong to this workspace",
        )

    try:
        approval_id_int = int(payload.approval_id)
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid approval_id: must be a valid numeric Snowflake ID",
        )

    try:
        result = execute_quick_approval(
            db=db,
            workspace_id=workspace_id,
            user_id=member.user_id,
            approval_id=approval_id_int,
            decision=payload.decision,
            reason=payload.reason,
        )
        return result
    except ValueError as val_err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(val_err),
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error executing quick approval: {str(exc)}",
        )
