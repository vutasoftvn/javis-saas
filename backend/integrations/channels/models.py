from datetime import datetime
from typing import Optional

from sqlalchemy import String, Boolean, DateTime, ForeignKey, BigInteger, func, UniqueConstraint, Text, Integer, Numeric, Float
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column, relationship
from pgvector.sqlalchemy import Vector

from db.base_class import Base
from db.snowflake_model import SnowflakeIDMixin


class MCPConnection(SnowflakeIDMixin, Base):
    __tablename__ = "mcp_connections"
    
    workspace_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("workspaces.id"), index=True)
    name: Mapped[str] = mapped_column(String(255))
    config_jsonb: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="disconnected")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class WorkspaceSecret(SnowflakeIDMixin, Base):
    __tablename__ = "workspace_secrets"
    __table_args__ = (
        UniqueConstraint('workspace_id', 'key', name='uix_secret_workspace_key'),
    )
    
    workspace_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("workspaces.id"), index=True)
    key: Mapped[str] = mapped_column(String(255))
    encrypted_value: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Chatbot(SnowflakeIDMixin, Base):
    __tablename__ = "chatbots"
    
    workspace_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("workspaces.id"), index=True)
    agent_id: Mapped[Optional[int]] = mapped_column(BigInteger, ForeignKey("agents.id"), nullable=True)
    name: Mapped[str] = mapped_column(String(255))
    channel: Mapped[str] = mapped_column(String(50)) # telegram, zalo
    channel_config_jsonb: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ChatbotConversation(SnowflakeIDMixin, Base):
    __tablename__ = "chatbot_conversations"
    
    chatbot_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("chatbots.id"), index=True)
    external_user_id: Mapped[str] = mapped_column(String(255), index=True)
    context_jsonb: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Plugin(SnowflakeIDMixin, Base):
    __tablename__ = "plugins"
    slug: Mapped[str] = mapped_column(String(255), unique=True)
    version: Mapped[str] = mapped_column(String(50))
    manifest_jsonb: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    trust_level: Mapped[str] = mapped_column(String(50), default="untrusted")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class WorkspacePlugin(SnowflakeIDMixin, Base):
    __tablename__ = "workspace_plugins"
    workspace_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("workspaces.id"), index=True)
    plugin_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("plugins.id"), index=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    granted_permissions: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Outbox(SnowflakeIDMixin, Base):
    __tablename__ = "outbox"
    workspace_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("workspaces.id"), index=True)
    channel: Mapped[str] = mapped_column(String(100))
    payload_jsonb: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="pending") # pending, sent, failed
    dedupe_key: Mapped[str] = mapped_column(String(255), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class EmailApproval(SnowflakeIDMixin, Base):
    """Một thư AI đã soạn, đang chờ người thật bấm duyệt mới được gửi."""
    __tablename__ = "email_approvals"

    workspace_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("workspaces.id"), index=True)
    chat_session_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, ForeignKey("chat_sessions.id", ondelete="CASCADE"), index=True, nullable=True
    )
    provider: Mapped[str] = mapped_column(String(50), default="gmail")
    draft_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    to_email: Mapped[str] = mapped_column(String(500))
    subject: Mapped[str] = mapped_column(String(998))
    body: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(50), default="pending")
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    decided_by: Mapped[Optional[int]] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=True)
    decided_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ZaloQrSession(SnowflakeIDMixin, Base):
    __tablename__ = "zalo_qr_sessions"

    workspace_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("workspaces.id"), index=True)
    created_by_user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), index=True)
    connection_id: Mapped[Optional[int]] = mapped_column(BigInteger, ForeignKey("mcp_connections.id"), nullable=True)
    state: Mapped[str] = mapped_column(String(24), default="queued", index=True)
    qr_data_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    claimed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
