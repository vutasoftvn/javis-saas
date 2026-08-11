"""Duyệt/gửi thư AI đã soạn. Mount dưới /api/v1/connectors/email-approvals.

Đây là ĐƯỜNG DUY NHẤT một email rời khỏi hòm thư người dùng. Model không có tool gửi thư,
nên muốn thư bay đi thì bắt buộc phải có người đăng nhập bấm vào endpoint này.
"""

import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.auth import get_current_workspace_member
from app.db.models import EmailApproval, WorkspaceMember
from app.db.session import get_db
from app.integrations.gmail_client import GmailError
from app.modules.integrations.google_connection_service import (
    GoogleNotConnected,
    build_gmail_client,
)

logger = logging.getLogger(__name__)

router = APIRouter()

BODY_PREVIEW_CHARS = 2000


def _serialize(approval: EmailApproval) -> dict:
    return {
        "id": str(approval.id),
        "chat_session_id": str(approval.chat_session_id) if approval.chat_session_id else None,
        "to": approval.to_email,
        "subject": approval.subject,
        "body": approval.body[:BODY_PREVIEW_CHARS],
        "status": approval.status,
        "error": approval.error,
        "created_at": approval.created_at.isoformat(),
        "decided_at": approval.decided_at.isoformat() if approval.decided_at else None,
    }


def _get_or_404(db: Session, approval_id: int, workspace_id: int) -> EmailApproval:
    # workspace_id đến từ query nhưng get_current_workspace_member đã chứng minh người gọi
    # là thành viên của CHÍNH workspace đó, nên lọc kèm nó là đủ chặn chéo tenant.
    approval = (
        db.query(EmailApproval)
        .filter(EmailApproval.id == approval_id, EmailApproval.workspace_id == workspace_id)
        .first()
    )
    if not approval:
        raise HTTPException(status_code=404, detail="Không tìm thấy thư chờ duyệt")
    return approval


@router.get("/email-approvals")
def list_email_approvals(
    workspace_id: int,
    session_id: int | None = None,
    status: str = "pending",
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    query = db.query(EmailApproval).filter(EmailApproval.workspace_id == workspace_id)
    if session_id:
        query = query.filter(EmailApproval.chat_session_id == session_id)
    if status != "all":
        query = query.filter(EmailApproval.status == status)

    approvals = query.order_by(EmailApproval.created_at.desc()).limit(50).all()
    return {"approvals": [_serialize(item) for item in approvals]}


@router.post("/email-approvals/{approval_id}/approve")
async def approve_email(
    approval_id: int,
    workspace_id: int,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    approval = _get_or_404(db, approval_id, workspace_id)
    if approval.status != "pending":
        # Bấm duyệt hai lần (hoặc hai người cùng bấm) không được gửi thư hai lần.
        raise HTTPException(
            status_code=409, detail=f"Thư này đã ở trạng thái '{approval.status}'"
        )
    if not approval.draft_id:
        raise HTTPException(status_code=400, detail="Thư này không có bản nháp để gửi")

    try:
        client = await build_gmail_client(db, workspace_id)
        await client.send_draft(approval.draft_id)
    except (GoogleNotConnected, GmailError) as exc:
        approval.status = "failed"
        approval.error = str(exc)
        db.commit()
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception:
        logger.exception("Gửi thư đã duyệt thất bại")
        approval.status = "failed"
        approval.error = "Gửi thư thất bại"
        db.commit()
        raise HTTPException(status_code=502, detail="Gửi thư thất bại, thử lại sau")

    approval.status = "sent"
    approval.error = None
    approval.decided_by = member.user_id
    approval.decided_at = datetime.utcnow()
    db.commit()
    return _serialize(approval)


@router.post("/email-approvals/{approval_id}/reject")
def reject_email(
    approval_id: int,
    workspace_id: int,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    """Từ chối chỉ đánh dấu ở COSA OS; bản nháp vẫn nằm trong Gmail để người dùng tự sửa
    hoặc xoá - xoá hộ dữ liệu trong hòm thư của họ không phải việc của ta."""
    approval = _get_or_404(db, approval_id, workspace_id)
    if approval.status != "pending":
        raise HTTPException(
            status_code=409, detail=f"Thư này đã ở trạng thái '{approval.status}'"
        )

    approval.status = "rejected"
    approval.decided_by = member.user_id
    approval.decided_at = datetime.utcnow()
    db.commit()
    return _serialize(approval)
