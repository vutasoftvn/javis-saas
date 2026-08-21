from datetime import datetime
from typing import Optional, List

from sqlalchemy import String, Boolean, DateTime, ForeignKey, BigInteger, func, UniqueConstraint, Text, Integer, Numeric, Float, Index, text
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column, relationship, object_session
from pgvector.sqlalchemy import Vector

from db.base_class import Base
from core.snowflake import generate_snowflake_id

class BscGoal(Base):
    """Mục tiêu Balanced Scorecard (Chỉ kích hoạt tại S5 & S6)."""
    __tablename__ = "bsc_goals"
    
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), index=True)
    
    # FINANCIAL | CUSTOMER | INTERNAL_OPERATIONS | LEARNING_GROWTH
    perspective: Mapped[str] = mapped_column(String(50), index=True)
    objective: Mapped[str] = mapped_column(String(255))
    kpi_name: Mapped[str] = mapped_column(String(255))
    target_value: Mapped[str] = mapped_column(String(100))
    current_value: Mapped[str] = mapped_column(String(100), default="0")
    
    initiatives: Mapped[dict] = mapped_column(JSONB, default=list)
    status: Mapped[str] = mapped_column(String(50), default="on_track") # on_track | at_risk | behind
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class BscScorecard(Base):
    __tablename__ = "bsc_scorecards"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    strategy_profile_id: Mapped[int] = mapped_column(ForeignKey("strategy_canvases.id"), index=True)
    period_start: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    period_end: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="draft")
    approved_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class StrategicObjective(Base):
    __tablename__ = "strategic_objectives"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    scorecard_id: Mapped[int] = mapped_column(ForeignKey("bsc_scorecards.id"), index=True)
    perspective: Mapped[str] = mapped_column(String(50))
    statement: Mapped[str] = mapped_column(Text)
    owner_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="draft")
    metric_id: Mapped[Optional[int]] = mapped_column(ForeignKey("metrics.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class StrategicObjectiveLink(Base):
    __tablename__ = "strategic_objective_links"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    from_objective_id: Mapped[int] = mapped_column(ForeignKey("strategic_objectives.id"), index=True)
    to_objective_id: Mapped[int] = mapped_column(ForeignKey("strategic_objectives.id"), index=True)
    relation_type: Mapped[str] = mapped_column(String(50))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
