from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from db.base_class import Base
from db.snowflake_model import SnowflakeIDMixin


class CapabilityGrant(SnowflakeIDMixin, Base):
    """Capability authorization grant for an agent, user, mini-app, or workflow."""
    __tablename__ = "capability_grants"

    workspace_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("core.workspaces.id"), index=True, nullable=False)
    company_id: Mapped[Optional[int]] = mapped_column(BigInteger, index=True, nullable=True)

    # Subject details
    subject_type: Mapped[str] = mapped_column(String(50), default="agent", nullable=False)  # agent, user, mini_app, workflow
    subject_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)  # agent_key or identifier

    # Capability and Resource scope
    capability: Mapped[str] = mapped_column(String(150), nullable=False, index=True)  # e.g. "sales.crm.read", "email.send"
    resource_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)  # e.g. "crm_lead", "email_account", "sandbox"
    resource_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)  # specific id or wildcard "*"
    scope_jsonb: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    # Grant metadata and lifecycle
    granted_by: Mapped[Optional[int]] = mapped_column(BigInteger, ForeignKey("core.users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    __table_args__ = (
        Index("ix_capability_grants_ws_subj_cap", "workspace_id", "subject_type", "subject_id", "capability"),
        {"schema": "agent_runtime"},
    )
