"""Cầu nối giữa bản ghi MCPConnection và một GmailClient dùng được.

Mọi đường vào Gmail đều đi qua đây để tenancy chỉ phải đúng ở MỘT chỗ: workspace_id luôn
lấy từ dữ liệu server (brain của chat session), không bao giờ từ tham số client gửi lên.
"""

import logging
import uuid

from sqlalchemy.orm import Session

from app.db.models import MCPConnection
from app.integrations.gmail_client import GmailClient
from app.modules.integrations import google_oauth_service
from app.modules.integrations.secrets_service import (
    decrypt_for_workspace,
    encrypt_for_workspace,
)

logger = logging.getLogger(__name__)

CONNECTOR_TYPE = "google_workspace"


class GoogleNotConnected(RuntimeError):
    """Workspace chưa đấu Gmail (hoặc bản ghi cũ không có token)."""


def get_google_connection(db: Session, workspace_id) -> MCPConnection | None:
    for connection in (
        db.query(MCPConnection).filter(MCPConnection.workspace_id == workspace_id).all()
    ):
        config = connection.config_jsonb or {}
        if config.get("type") == CONNECTOR_TYPE:
            return connection
    return None


def has_usable_google_connection(db: Session, workspace_id) -> bool:
    """Có kết nối kèm refresh token thật hay không.

    Bản ghi "kết nối" kiểu cũ (chỉ có email người dùng gõ tay, status='connected') KHÔNG
    tính - chính nó là thứ khiến chat hứa đọc được mail rồi không đọc được.
    """
    connection = get_google_connection(db, workspace_id)
    return bool(connection and (connection.config_jsonb or {}).get("refresh_token"))


def store_connection(
    db: Session, workspace_id: uuid.UUID, email: str, refresh_token: str
) -> MCPConnection:
    connection = get_google_connection(db, workspace_id)
    config = {
        "type": CONNECTOR_TYPE,
        "email": email,
        "scopes": google_oauth_service.SCOPES,
        "refresh_token": encrypt_for_workspace(workspace_id, refresh_token),
    }

    if connection is None:
        connection = MCPConnection(
            workspace_id=workspace_id,
            name=f"Google Workspace ({email})",
            config_jsonb=config,
            status="connected",
        )
        db.add(connection)
    else:
        # Gán cả dict mới thay vì sửa tại chỗ: SQLAlchemy không theo dõi thay đổi bên trong
        # JSONB, sửa tại chỗ là commit xong DB vẫn giữ giá trị cũ.
        connection.name = f"Google Workspace ({email})"
        connection.config_jsonb = config
        connection.status = "connected"

    db.commit()
    db.refresh(connection)
    return connection


def get_refresh_token(db: Session, workspace_id) -> str:
    connection = get_google_connection(db, workspace_id)
    if not connection:
        raise GoogleNotConnected("Workspace chưa kết nối Gmail")

    stored = (connection.config_jsonb or {}).get("refresh_token")
    if not stored:
        raise GoogleNotConnected(
            "Kết nối Gmail này được tạo trước khi có đăng nhập Google thật nên không dùng "
            "được. Hãy vào Kết nối, xoá nó và bấm kết nối lại."
        )

    token = decrypt_for_workspace(workspace_id, stored)
    if not token:
        raise GoogleNotConnected("Không giải mã được token Gmail, hãy kết nối lại.")
    return token


async def build_gmail_client(db: Session, workspace_id) -> GmailClient:
    """Access token chỉ sống 1 giờ nên xin mới mỗi lượt thay vì lưu lại và đoán hạn."""
    refresh_token = get_refresh_token(db, workspace_id)
    access_token = await google_oauth_service.refresh_access_token(refresh_token)
    if not access_token:
        raise GoogleNotConnected("Google không cấp access token, hãy kết nối lại.")
    return GmailClient(access_token)


def connected_email(db: Session, workspace_id) -> str:
    connection = get_google_connection(db, workspace_id)
    return (connection.config_jsonb or {}).get("email", "") if connection else ""
