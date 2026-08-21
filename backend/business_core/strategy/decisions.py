from datetime import datetime
from typing import Optional, List

from sqlalchemy import String, Boolean, DateTime, ForeignKey, BigInteger, func, UniqueConstraint, Text, Integer, Numeric, Float, Index, text
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column, relationship, object_session
from pgvector.sqlalchemy import Vector

from db.base_class import Base
from core.snowflake import generate_snowflake_id

class StrategicDecision(Base):
    __tablename__ = "strategic_decisions"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    brain_id: Mapped[int] = mapped_column(ForeignKey("brains.id"), index=True)
    project_id: Mapped[Optional[int]] = mapped_column(ForeignKey("projects.id"), nullable=True, index=True)
    context_pack_id: Mapped[Optional[int]] = mapped_column(ForeignKey("context_packs.id"), nullable=True, index=True)
    tows_option_id: Mapped[Optional[int]] = mapped_column(ForeignKey("tows_options.id"), nullable=True)
    question: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    decision: Mapped[str] = mapped_column(Text)
    selected_option: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    alternatives_jsonb: Mapped[dict] = mapped_column(JSONB, default=list)
    rationale: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    rationale_revision_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    evidence_refs: Mapped[dict] = mapped_column(JSONB, default=list)
    stage: Mapped[str] = mapped_column(String(50), default="S1_PROBLEM_VALIDATION")
    expected_result: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    review_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="active")
    decided_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class GateDecision(Base):
    __tablename__ = "gate_decisions"
    __table_args__ = (Index("ix_gate_decision_mvp_stage_id", "mvp_stage_id"),)
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    milestone_id: Mapped[Optional[int]] = mapped_column(ForeignKey("milestones.id", ondelete="SET NULL"), nullable=True, index=True)
    stage_id: Mapped[Optional[int]] = mapped_column(ForeignKey("cycle_stages.id", ondelete="SET NULL"), nullable=True, index=True)
    # MVP-stage Week 13 gate decisions set this instead of stage_id (CycleStage).
    mvp_stage_id: Mapped[Optional[int]] = mapped_column(ForeignKey("mvp_stages.id", ondelete="SET NULL"), nullable=True)
    decision: Mapped[str] = mapped_column(String(50))  # GO, ITERATE, HOLD, STOP, PIVOT
    rationale: Mapped[str] = mapped_column(Text)
    evidence_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    evidence_refs: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    next_step_instructions: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    decided_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    decided_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class ModelRunAudit(Base):
    """Nhật ký kiểm toán thực thi mô hình AI (Model Runs Audit Table)."""
    __tablename__ = "model_runs_audit"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    model_profile: Mapped[str] = mapped_column(String(100), default="TERRA_V12")
    prompt_tokens: Mapped[int] = mapped_column(Integer, default=0)
    completion_tokens: Mapped[int] = mapped_column(Integer, default=0)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(50), default="success")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class ModelProfileOverride(Base):
    """Ghi đè cấu hình theo workspace cho logical model profile (chat/model_profiles.py §56).

    Chỉ lưu override admin-facing (display_name/temperature/is_active); việc chọn
    (provider, model) thực tế vẫn do chat/model_profiles.resolve_profile() quyết định
    qua env var - bảng này không nhân bản logic đó.
    """
    __tablename__ = "model_profile_overrides"
    __table_args__ = (
        UniqueConstraint('workspace_id', 'profile_key', name='uix_model_profile_override_ws_key'),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    profile_key: Mapped[str] = mapped_column(String(100))  # STRATEGIC_ANALYZER, CONVERSATION_ROUTER, DEVELOPER_WORKER
    display_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    temperature: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

# ==========================================
# COSA Stage-Aware — Stage Gate Auditing & Anti-Premature Scaling (Phase 4)
# ==========================================
