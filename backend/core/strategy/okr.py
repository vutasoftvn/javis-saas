from datetime import datetime
from typing import Optional, List

from sqlalchemy import String, Boolean, DateTime, ForeignKey, BigInteger, func, UniqueConstraint, Text, Integer, Numeric, Float, Index, text
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column, relationship, object_session
from pgvector.sqlalchemy import Vector

from app.db.base_class import Base
from app.core.snowflake import generate_snowflake_id

class OkrCycle(Base):
    __tablename__ = "okr_cycles"
    __table_args__ = (Index("ix_okr_cycle_mvp_stage_id", "mvp_stage_id"),)
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    brain_id: Mapped[int] = mapped_column(ForeignKey("brains.id"), index=True)
    # References MvpStage, not the unrelated CycleStage - see WeeklyPlan.stage_id.
    mvp_stage_id: Mapped[Optional[int]] = mapped_column(ForeignKey("mvp_stages.id"), nullable=True)
    name: Mapped[str] = mapped_column(String(255))
    start_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    end_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="draft")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class OkrObjective(Base):
    __tablename__ = "okr_objectives"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    cycle_id: Mapped[int] = mapped_column(ForeignKey("okr_cycles.id"), index=True)
    strategic_objective_id: Mapped[Optional[int]] = mapped_column(ForeignKey("strategic_objectives.id"), nullable=True)
    title: Mapped[str] = mapped_column(String(255))
    # Retained for existing objective rationale and compatibility with the
    # additive traceability migration. A capability should not lose its context
    # just because a later UI no longer displays it.
    why: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    owner_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="draft")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class KeyResult(Base):
    __tablename__ = "key_results"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    objective_id: Mapped[int] = mapped_column(ForeignKey("okr_objectives.id"), index=True)
    title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    metric_id: Mapped[Optional[int]] = mapped_column(ForeignKey("metrics.id"), nullable=True)
    baseline_value: Mapped[Optional[float]] = mapped_column(nullable=True)
    current_value: Mapped[Optional[float]] = mapped_column(nullable=True)
    target_value: Mapped[Optional[float]] = mapped_column(nullable=True)
    unit: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    cadence: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    # Existing installations store these attributes on the key result. Metric
    # carries the same portable metadata for newly-created metric definitions;
    # keeping this data readable avoids a destructive schema rewrite.
    metric_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    evidence_refs: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="draft")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class OkrLink(Base):
    __tablename__ = "okr_links"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    from_entity_type: Mapped[str] = mapped_column(String(50))
    from_entity_id: Mapped[int] = mapped_column(BigInteger, index=True)
    to_entity_type: Mapped[str] = mapped_column(String(50))
    to_entity_id: Mapped[int] = mapped_column(BigInteger, index=True)
    relation_type: Mapped[str] = mapped_column(String(50))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
