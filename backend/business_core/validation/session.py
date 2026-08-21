from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any, List

from sqlalchemy import String, Boolean, DateTime, ForeignKey, BigInteger, Text, Integer, Float, Index, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.base_class import Base
from core.snowflake import generate_snowflake_id
from business_core.validation.enums import ValidationWorkflowState, EpistemicType, ClaimConfirmationStatus, DimensionName, DimensionStateEnum, FeasibilityPillar


class ValidationSession(Base):
    """
    Quản lý phiên phỏng vấn / kiểm chứng dự án.
    """
    __tablename__ = "validation_sessions"
    __table_args__ = {"schema": "validation"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("core.workspaces.id"), index=True)
    brain_id: Mapped[int] = mapped_column(ForeignKey("knowledge.brains.id"), index=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("strategy.projects.id"), index=True)

    current_topic: Mapped[str] = mapped_column(String(50), default=DimensionName.CUSTOMER.value)
    workflow_state: Mapped[str] = mapped_column(String(50), default=ValidationWorkflowState.UNASSESSED.value, index=True)
    
    interview_mode_active: Mapped[bool] = mapped_column(Boolean, default=False)
    fields_status_jsonb: Mapped[dict] = mapped_column(JSONB, default=dict)
    session_metadata: Mapped[dict] = mapped_column(JSONB, default=dict)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class StructuredClaim(Base):
    """
    Dữ kiện có cấu trúc bóc tách từ hội thoại hoặc nguồn khác (F1.md §51).
    """
    __tablename__ = "structured_claims"
    __table_args__ = {"schema": "validation"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("core.workspaces.id"), index=True)
    brain_id: Mapped[int] = mapped_column(ForeignKey("knowledge.brains.id"), index=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("strategy.projects.id"), index=True)
    session_id: Mapped[Optional[int]] = mapped_column(ForeignKey("validation.validation_sessions.id"), nullable=True, index=True)

    dimension: Mapped[str] = mapped_column(String(50), index=True)
    subject: Mapped[str] = mapped_column(String(100), index=True)
    predicate: Mapped[str] = mapped_column(String(100), index=True)
    value_jsonb: Mapped[dict] = mapped_column(JSONB, default=dict)
    
    epistemic_type: Mapped[str] = mapped_column(String(50), default=EpistemicType.ASSUMPTION.value, index=True)
    confirmation_status: Mapped[str] = mapped_column(String(50), default=ClaimConfirmationStatus.AI_INFERRED.value, index=True)
    
    source_type: Mapped[str] = mapped_column(String(50), default="FOUNDER_CHAT")
    source_actor: Mapped[str] = mapped_column(String(50), default="FOUNDER")
    source_ref: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    confidence: Mapped[float] = mapped_column(Float, default=1.0)
    
    supersedes_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class FieldRevision(Base):
    """
    Lưu vết sửa đổi bất biến khi dữ liệu thay đổi (F1.md §52).
    """
    __tablename__ = "field_revisions"
    __table_args__ = {"schema": "validation"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("core.workspaces.id"), index=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("strategy.projects.id"), index=True)
    claim_id: Mapped[Optional[int]] = mapped_column(ForeignKey("validation.structured_claims.id"), nullable=True, index=True)

    field_path: Mapped[str] = mapped_column(String(255), index=True)
    old_value_jsonb: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    new_value_jsonb: Mapped[dict] = mapped_column(JSONB, default=dict)
    
    changed_by: Mapped[str] = mapped_column(String(50), default="FOUNDER")
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class DimensionState(Base):
    """
    State Vector đa chiều của từng Dimension trong Dự án (F1.md §9, §10).
    """
    __tablename__ = "dimension_states"
    __table_args__ = (
        UniqueConstraint("project_id", "dimension", name="uq_dimension_state_project_dim"),
        {"schema": "validation"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("core.workspaces.id"), index=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("strategy.projects.id"), index=True)

    dimension: Mapped[str] = mapped_column(String(50), index=True)
    pillar: Mapped[str] = mapped_column(String(50), default=FeasibilityPillar.DESIRABILITY.value)
    
    state: Mapped[str] = mapped_column(String(50), default=DimensionStateEnum.UNKNOWN.value, index=True)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class ProjectStageHistory(Base):
    """
    Lịch sử chuyển dịch Stage của Dự án (F1.md §50, §65).
    """
    __tablename__ = "project_stage_history"
    __table_args__ = {"schema": "validation"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("core.workspaces.id"), index=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("strategy.projects.id"), index=True)

    from_stage: Mapped[str] = mapped_column(String(50))
    to_stage: Mapped[str] = mapped_column(String(50))
    transition_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    approved_by: Mapped[Optional[int]] = mapped_column(ForeignKey("core.users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
