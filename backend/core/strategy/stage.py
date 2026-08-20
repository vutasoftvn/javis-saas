from datetime import datetime
from typing import Optional, List

from sqlalchemy import String, Boolean, DateTime, ForeignKey, BigInteger, func, UniqueConstraint, Text, Integer, Numeric, Float, Index, text
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column, relationship, object_session
from pgvector.sqlalchemy import Vector

from app.db.base_class import Base
from app.core.snowflake import generate_snowflake_id

class StageRevision(Base):
    __tablename__ = "stage_revisions"
    __table_args__ = (
        UniqueConstraint("mvp_stage_id", "revision_no", name="uq_stage_revision_stage_no"),
        Index("ix_stage_revision_workspace_stage", "workspace_id", "mvp_stage_id"),
    )
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    brain_id: Mapped[int] = mapped_column(ForeignKey("brains.id"), index=True)
    mvp_stage_id: Mapped[int] = mapped_column(ForeignKey("mvp_stages.id"), index=True)
    revision_no: Mapped[int] = mapped_column(Integer)
    change_type: Mapped[str] = mapped_column(String(24), default="MINOR")  # MINOR, MATERIAL
    before_snapshot_jsonb: Mapped[dict] = mapped_column(JSONB, default=dict)
    after_snapshot_jsonb: Mapped[dict] = mapped_column(JSONB, default=dict)
    impact_preview_jsonb: Mapped[dict] = mapped_column(JSONB, default=dict)
    status: Mapped[str] = mapped_column(String(24), default="PREVIEWED")  # PREVIEWED, APPLIED
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    applied_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class StageServiceAssessment(Base):
    __tablename__ = "stage_service_assessments"
    __table_args__ = (
        Index("ix_stage_assessment_workspace_stage", "workspace_id", "mvp_stage_id"),
    )
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    brain_id: Mapped[int] = mapped_column(ForeignKey("brains.id"), index=True)
    mvp_stage_id: Mapped[int] = mapped_column(ForeignKey("mvp_stages.id"), index=True)
    capability_id: Mapped[int] = mapped_column(ForeignKey("capability_definitions.id"), index=True)
    disposition: Mapped[str] = mapped_column(String(24))  # REQUIRED, RECOMMENDED, OPTIONAL
    reason: Mapped[str] = mapped_column(Text)
    risk_level: Mapped[str] = mapped_column(String(24), default="LOW")
    expected_output: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    execution_mode: Mapped[str] = mapped_column(String(24), default="MANUAL")
    professional_review_required: Mapped[bool] = mapped_column(Boolean, default=False)
    is_available: Mapped[bool] = mapped_column(Boolean, default=True)
    status: Mapped[str] = mapped_column(String(24), default="DRAFT")  # DRAFT, CONFIRMED, REJECTED
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class StageAssignment(Base):
    __tablename__ = "stage_assignments"
    __table_args__ = (
        Index("ix_stage_assignment_workspace_stage", "workspace_id", "mvp_stage_id"),
    )
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    brain_id: Mapped[int] = mapped_column(ForeignKey("brains.id"), index=True)
    mvp_stage_id: Mapped[int] = mapped_column(ForeignKey("mvp_stages.id"), index=True)
    assessment_id: Mapped[int] = mapped_column(ForeignKey("stage_service_assessments.id"), index=True)
    agent_id: Mapped[Optional[int]] = mapped_column(ForeignKey("workspace_agents.id"), nullable=True)
    weekly_commitment_id: Mapped[Optional[int]] = mapped_column(ForeignKey("weekly_commitments.id"), nullable=True)
    title: Mapped[str] = mapped_column(String(255))
    execution_mode: Mapped[str] = mapped_column(String(24), default="MANUAL")
    status: Mapped[str] = mapped_column(String(24), default="DRAFT")  # DRAFT, APPROVED, IN_PROGRESS, DONE, BLOCKED
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class StrategyAuditEvent(Base):
    __tablename__ = "strategy_audit_events"
    __table_args__ = (
        Index("ix_strategy_audit_workspace_project", "workspace_id", "project_id"),
    )
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    project_id: Mapped[Optional[int]] = mapped_column(ForeignKey("projects.id"), nullable=True, index=True)
    mvp_stage_id: Mapped[Optional[int]] = mapped_column(ForeignKey("mvp_stages.id"), nullable=True, index=True)
    event_type: Mapped[str] = mapped_column(String(50))  # AI_RECOMMENDATION, FOUNDER_DECISION, AGENT_ACTION, HUMAN_REVIEW
    actor_type: Mapped[str] = mapped_column(String(24))  # AI, FOUNDER, AGENT, HUMAN_REVIEWER
    actor_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    summary: Mapped[str] = mapped_column(Text)
    payload_jsonb: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
