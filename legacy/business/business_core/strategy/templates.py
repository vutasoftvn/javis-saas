from datetime import datetime
from typing import Optional, List

from sqlalchemy import String, Boolean, DateTime, ForeignKey, BigInteger, func, UniqueConstraint, Text, Integer, Numeric, Float, Index, text
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column, relationship, object_session
from pgvector.sqlalchemy import Vector

from db.base_class import Base
from core.snowflake import generate_snowflake_id

class WorkspaceTemplate(Base):
    __tablename__ = "workspace_templates"
    __table_args__ = (UniqueConstraint("workspace_id", "source_key", name="uq_workspace_template_source"), {"schema": "strategy"})
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("core.workspaces.id"), index=True)
    brain_id: Mapped[int] = mapped_column(ForeignKey("knowledge.brains.id"), index=True)
    name: Mapped[str] = mapped_column(String(255))
    source_key: Mapped[str] = mapped_column(String(100))
    active_version_no: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class WorkspaceTemplateVersion(Base):
    __tablename__ = "workspace_template_versions"
    __table_args__ = (UniqueConstraint("template_id", "version_no", name="uq_workspace_template_version"), {"schema": "strategy"})
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("core.workspaces.id"), index=True)
    template_id: Mapped[int] = mapped_column(ForeignKey("strategy.workspace_templates.id"), index=True)
    version_no: Mapped[int] = mapped_column(Integer)
    config_jsonb: Mapped[dict] = mapped_column(JSONB, default=dict)
    source_seed_key: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    playbook_document_id: Mapped[Optional[int]] = mapped_column(ForeignKey("knowledge.vault_documents.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(24), default="ACTIVE")  # ACTIVE, ARCHIVED
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class PromptTemplate(Base):
    __tablename__ = "prompt_templates"
    __table_args__ = {"schema": "strategy"}
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[Optional[int]] = mapped_column(ForeignKey("core.workspaces.id"), nullable=True, index=True)
    brain_id: Mapped[Optional[int]] = mapped_column(ForeignKey("knowledge.brains.id"), nullable=True, index=True)
    feature_key: Mapped[str] = mapped_column(String(50), default="STRATEGY_ANALYSIS", index=True)
    name: Mapped[str] = mapped_column(String(255), default="Phân tích Chiến lược (PESTEL, SWOT, TOWS)")
    template_content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    config_jsonb: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ==========================================
# mCOSA V12 — Weekly Review & Week 13 Strategic Transition (Sprint 5)
# ==========================================
