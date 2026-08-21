"""Workspace-scoped API for the durable Zalo QR connector."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from core.auth import get_current_user
from core.id_types import parse_snowflake_id
from db.models import User, WorkspaceMember
from db.session import get_db
from integrations.channels.zalo.zalo_qr_service import (
    cancel_qr_session,
    create_qr_session,
    get_qr_session_for_owner,
)

router = APIRouter()


class ZaloStartRequest(BaseModel):
    workspace_id: int


def _not_found() -> HTTPException:
    return HTTPException(status_code=404, detail="Phiên đăng nhập QR không tồn tại hoặc đã hết hạn")


def get_zalo_workspace_member(
    workspace_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> WorkspaceMember:
    """Do not reveal whether another workspace or its QR session exists."""
    member = db.query(WorkspaceMember).filter(
        WorkspaceMember.workspace_id == workspace_id,
        WorkspaceMember.user_id == current_user.id,
    ).first()
    if member is None:
        raise _not_found()
    return member


def _serialize(session) -> dict:
    return {
        "id": str(session.id),
        "state": session.state,
        "qr": session.qr_data_url or "",
        "connection_id": str(session.connection_id) if session.connection_id else None,
        "error": session.error or "",
        "expires_at": session.expires_at.isoformat(),
    }


@router.post("/zalo/sessions", status_code=202)
def start_zalo_qr(
    data: ZaloStartRequest,
    member: WorkspaceMember = Depends(get_zalo_workspace_member),
    db: Session = Depends(get_db),
):
    session = create_qr_session(db, data.workspace_id, member.user_id)
    return _serialize(session)


@router.get("/zalo/sessions/{session_id}")
def get_zalo_qr_status(
    session_id: str,
    workspace_id: int,
    member: WorkspaceMember = Depends(get_zalo_workspace_member),
    db: Session = Depends(get_db),
):
    try:
        identifier = parse_snowflake_id(session_id)
    except ValueError:
        raise _not_found()
    session = get_qr_session_for_owner(db, identifier, workspace_id, member.user_id)
    if session is None:
        raise _not_found()
    return _serialize(session)


@router.post("/zalo/sessions/{session_id}/cancel")
def cancel_zalo_qr(
    session_id: str,
    workspace_id: int,
    member: WorkspaceMember = Depends(get_zalo_workspace_member),
    db: Session = Depends(get_db),
):
    try:
        identifier = parse_snowflake_id(session_id)
    except ValueError:
        raise _not_found()
    session = get_qr_session_for_owner(db, identifier, workspace_id, member.user_id)
    if session is None:
        raise _not_found()
    cancel_qr_session(db, session)
    return {"status": "success", "id": str(session.id), "state": session.state}
