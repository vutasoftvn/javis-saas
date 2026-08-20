from datetime import datetime
from typing import Optional, List

from sqlalchemy import String, Boolean, DateTime, ForeignKey, BigInteger, func, UniqueConstraint, Text, Integer, Numeric, Float, Index, text
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column, relationship, object_session
from pgvector.sqlalchemy import Vector

from app.db.base_class import Base
from app.core.snowflake import generate_snowflake_id

class EvidenceItem(Base):
    # Evidence là entity workspace-scoped, tái dùng được qua nhiều Context Pack -
    # khác với context_pack_sources.citation_jsonb cũ (blob gắn chết vào 1 context
    # pack). Cột đặt tên "tags" thay vì "metadata" theo DDL mẫu spec vì "metadata" là
    # tên thuộc tính dành riêng cho Base.metadata của SQLAlchemy declarative.
    __tablename__ = "evidence_items"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    title: Mapped[str] = mapped_column(String(255))
    summary: Mapped[str] = mapped_column(Text)
    source_type: Mapped[str] = mapped_column(String(50))  # customer_interview, market_report, internal_metric, regulation, competitor, note
    source_url_or_vault_uri: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    captured_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    reliability: Mapped[str] = mapped_column(String(50))  # high, medium, low
    tags: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class ContextPack(Base):
    __tablename__ = "context_packs"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    strategy_revision_id: Mapped[Optional[int]] = mapped_column(ForeignKey("strategy_revisions.id"), nullable=True, index=True)
    business_context: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    internal_resources: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="draft")  # draft, ready_for_review, approved, stale, superseded
    approved_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class ContextPackSource(Base):
    __tablename__ = "context_pack_sources"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    context_pack_id: Mapped[int] = mapped_column(ForeignKey("context_packs.id"), index=True)
    # Legacy: id của một vault_revision cụ thể (giữ nguyên ý nghĩa cũ). Nullable vì
    # luồng evidence_items mới (Strategic Canvas 1-1-3) không gắn với vault revision.
    revision_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True, index=True)
    evidence_id: Mapped[Optional[int]] = mapped_column(ForeignKey("evidence_items.id"), nullable=True, index=True)
    source_type: Mapped[str] = mapped_column(String(50))
    citation_jsonb: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    included_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)

class Hypothesis(Base):
    """Giả định cốt lõi của Startup / Project theo chuẩn COSA Stage-Aware."""
    __tablename__ = "hypotheses"
    
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), index=True)
    
    # customer | problem | solution | pricing | channel | revenue | cost | technology | legal | operational
    category: Mapped[str] = mapped_column(String(50), index=True)
    statement: Mapped[str] = mapped_column(Text)
    
    importance: Mapped[float] = mapped_column(Float, default=0.5)  # 0.0 - 1.0
    uncertainty: Mapped[float] = mapped_column(Float, default=0.5) # 0.0 - 1.0
    risk_score: Mapped[float] = mapped_column(Float, default=0.25) # importance * uncertainty
    
    evidence_score: Mapped[float] = mapped_column(Float, default=0.0) # 0.0 - 1.0 (tính từ Evidence Ladder)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    
    # UNTESTED | TESTING | SUPPORTED | CONTRADICTED | INVALIDATED
    status: Mapped[str] = mapped_column(String(50), default="UNTESTED", index=True)
    stage_created: Mapped[str] = mapped_column(String(50), default="S1_PROBLEM_VALIDATION")
    
    evidence_refs: Mapped[dict] = mapped_column(JSONB, default=list) # List[int]: evidence_ids
    experiment_refs: Mapped[dict] = mapped_column(JSONB, default=list)
    
    next_action: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Evidence(Base):
    """Bằng chứng kiểm chứng thực tế theo Thang đo Evidence Ladder (E0 -> E6)."""
    __tablename__ = "evidences"
    
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), index=True)
    
    # interview | observation | behavioral | transaction | usage | campaign | financial | legal | market_signal
    type: Mapped[str] = mapped_column(String(50), index=True)
    
    # E0_OPINION .. E6_SCALABLE_EVIDENCE
    ladder_level: Mapped[str] = mapped_column(String(50), default="E1_STATED_INTEREST", index=True)
    source: Mapped[str] = mapped_column(String(255))
    claim_supported: Mapped[str] = mapped_column(Text)
    
    strength: Mapped[str] = mapped_column(String(50), default="medium") # weak | medium | strong
    direction: Mapped[str] = mapped_column(String(50), default="supports") # supports | contradicts | neutral
    
    hypothesis_refs: Mapped[dict] = mapped_column(JSONB, default=list) # List[int]: hypothesis_ids
    artifact_refs: Mapped[dict] = mapped_column(JSONB, default=list)   # List[int]: vault_document_ids
    raw_payload: Mapped[dict] = mapped_column(JSONB, default=dict)
    
    captured_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class MilestoneEvidence(Base):
    __tablename__ = "milestone_evidence"
    __table_args__ = (
        UniqueConstraint('milestone_id', 'evidence_id', name='uix_milestone_evidence_milestone_evidence'),
    )
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    milestone_id: Mapped[int] = mapped_column(ForeignKey("milestones.id", ondelete="CASCADE"), index=True)
    evidence_id: Mapped[int] = mapped_column(ForeignKey("evidence_items.id", ondelete="CASCADE"), index=True)
    relevance_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
