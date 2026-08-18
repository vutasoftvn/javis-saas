"""SQLAlchemy Models for Business Knowledge Pack (Spec E1)."""
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from sqlalchemy import BigInteger, String, Text, DateTime, Boolean, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import Base
from app.db.snowflake_model import SnowflakeIDMixin
from app.core.snowflake import generate_snowflake_id


class BusinessPackModel(SnowflakeIDMixin, Base):
    """Business Pack Registry / Status for Workspace."""
    __tablename__ = "business_packs"

    workspace_id: Mapped[Optional[int]] = mapped_column(BigInteger, ForeignKey("workspaces.id"), index=True, nullable=True)
    pack_id: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    domain: Mapped[str] = mapped_column(String(50), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    version: Mapped[str] = mapped_column(String(50), nullable=False, default="1.0.0")
    status: Mapped[str] = mapped_column(String(30), default="active")  # active, disabled
    is_factory: Mapped[bool] = mapped_column(Boolean, default=True)
    manifest_jsonb: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False
    )

    __table_args__ = (
        UniqueConstraint("workspace_id", "pack_id", name="uq_business_packs_ws_pack"),
    )


class BusinessAssetOverrideModel(SnowflakeIDMixin, Base):
    """Company-level Local Asset Overrides (Templates, SOPs, Capabilities)."""
    __tablename__ = "business_asset_overrides"

    workspace_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("workspaces.id"), index=True, nullable=False)
    asset_id: Mapped[str] = mapped_column(String(150), index=True, nullable=False)
    asset_type: Mapped[str] = mapped_column(String(50), nullable=False)  # template, sop, capability, reference
    pack_id: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    version: Mapped[str] = mapped_column(String(50), default="1.0.0")
    
    # Override content
    content_override_jsonb: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict)
    body_override_markdown: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    updated_by: Mapped[Optional[int]] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False
    )

    __table_args__ = (
        UniqueConstraint("workspace_id", "asset_id", name="uq_asset_override_ws_asset"),
    )


class LegalSourceRecord(SnowflakeIDMixin, Base):
    """Immutable Legal Source Reference Records."""
    __tablename__ = "legal_sources"

    source_id: Mapped[str] = mapped_column(String(150), unique=True, index=True, nullable=False)
    jurisdiction: Mapped[str] = mapped_column(String(20), default="VN", index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    document_type: Mapped[str] = mapped_column(String(50), default="law")
    identifier: Mapped[str] = mapped_column(String(100), default="")
    issuer: Mapped[str] = mapped_column(String(150), default="")
    effective_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    expiry_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="current", index=True)  # current, amended, superseded, expired, unknown
    version: Mapped[str] = mapped_column(String(30), default="1")
    tags: Mapped[List[str]] = mapped_column(JSONB, default=list)
    metadata_jsonb: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict)
    text_content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False
    )


class LegalAnnotationRecord(SnowflakeIDMixin, Base):
    """Company-specific Legal Annotations and Applicability Rules."""
    __tablename__ = "legal_annotations"

    workspace_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("workspaces.id"), index=True, nullable=False)
    legal_source_id: Mapped[str] = mapped_column(String(150), index=True, nullable=False)
    applicability_status: Mapped[str] = mapped_column(String(30), default="applicable")
    business_areas: Mapped[List[str]] = mapped_column(JSONB, default=list)
    notes: Mapped[List[str]] = mapped_column(JSONB, default=list)
    linked_sops: Mapped[List[str]] = mapped_column(JSONB, default=list)
    linked_templates: Mapped[List[str]] = mapped_column(JSONB, default=list)
    
    reviewed_by: Mapped[Optional[int]] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=True)
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False
    )

    __table_args__ = (
        UniqueConstraint("workspace_id", "legal_source_id", name="uq_legal_annotation_ws_source"),
    )
