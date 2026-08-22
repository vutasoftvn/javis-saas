from datetime import datetime
from typing import Optional, List

from sqlalchemy import String, Boolean, DateTime, ForeignKey, BigInteger, func, UniqueConstraint, Text, Integer, Numeric, Float, Index, text
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column, relationship, object_session
from pgvector.sqlalchemy import Vector

from db.base_class import Base
from core.snowflake import generate_snowflake_id

class Metric(Base):
    __tablename__ = "metrics"
    __table_args__ = {"schema": "strategy"}
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("core.workspaces.id"), index=True)
    brain_id: Mapped[int] = mapped_column(ForeignKey("knowledge.brains.id"), index=True)
    name: Mapped[str] = mapped_column(String(255))
    formula: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    unit: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    baseline_value: Mapped[Optional[float]] = mapped_column(nullable=True)
    target_value: Mapped[Optional[float]] = mapped_column(nullable=True)
    data_source: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    cadence: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    metric_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    evidence_refs: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class MetricCheckin(Base):
    __tablename__ = "metric_checkins"
    __table_args__ = {"schema": "strategy"}
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("core.workspaces.id"), index=True)
    metric_id: Mapped[int] = mapped_column(ForeignKey("strategy.metrics.id"), index=True)
    as_of_at: Mapped[datetime] = mapped_column(DateTime)
    value: Mapped[float] = mapped_column()
    source_ref: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    entered_by: Mapped[Optional[int]] = mapped_column(ForeignKey("core.users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
