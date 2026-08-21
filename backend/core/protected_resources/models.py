"""SQLAlchemy models for Protected Resources and their revisions.

Provides default+override pattern, immutable defaults, versioning, and reset capability.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.base_class import Base
from db.snowflake_model import SnowflakeIDMixin


class ProtectedResource(SnowflakeIDMixin, Base):
    """Represents a protected configuration or resource (Prompt, Spec, Skill, Policy, Priming)."""

    __tablename__ = "protected_resources"
    __table_args__ = (
        UniqueConstraint("workspace_id", "resource_type", "resource_key", name="uix_protected_resources_ws_type_key"),
        {"schema": "agent_runtime"},
    )

    workspace_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("workspaces.id"), index=True, nullable=False)
    resource_type: Mapped[str] = mapped_column(String(50), index=True, nullable=False)  # "agent_prompt", "spec", "skill", "policy", "priming", "profile"
    resource_key: Mapped[str] = mapped_column(String(255), index=True, nullable=False)  # e.g. "agent:{agent_id}:system_prompt"
    active_revision_no: Mapped[int] = mapped_column(Integer, default=0, nullable=False)  # 0 = bundled default
    editable_by: Mapped[list] = mapped_column(JSONB, default=lambda: ["admin"], nullable=False)
    resettable: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    revisions = relationship("ProtectedResourceRevision", back_populates="resource", cascade="all, delete-orphan")


class ProtectedResourceRevision(SnowflakeIDMixin, Base):
    """Represents a specific revision of a protected resource."""

    __tablename__ = "protected_resource_revisions"
    __table_args__ = (
        UniqueConstraint("resource_id", "revision_no", name="uix_protected_resource_revisions_res_rev"),
        {"schema": "agent_runtime"},
    )

    resource_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("agent_runtime.protected_resources.id"), index=True, nullable=False)
    revision_no: Mapped[int] = mapped_column(Integer, nullable=False)
    content_jsonb: Mapped[dict] = mapped_column(JSONB, nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)  # revision 0 = bundled default
    status: Mapped[str] = mapped_column(String(24), default="ACTIVE", nullable=False)  # ACTIVE, ARCHIVED
    created_by: Mapped[Optional[int]] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=True)
    checksum: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    resource = relationship("ProtectedResource", back_populates="revisions")
