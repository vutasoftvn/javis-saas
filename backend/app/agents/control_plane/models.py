from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base
from app.db.snowflake_model import SnowflakeIDMixin


class AgentGoal(SnowflakeIDMixin, Base):
    """Business or project goal supplied by the Founder/User as the top-level agentic entrypoint."""
    __tablename__ = "agent_goals"

    workspace_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("workspaces.id"), index=True, nullable=False)
    company_id: Mapped[Optional[int]] = mapped_column(BigInteger, index=True, nullable=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), index=True, nullable=False)

    goal_type: Mapped[str] = mapped_column(String(50), default="business_goal", nullable=False)  # business_goal, project_goal, campaign_goal
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    target_metric_jsonb: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)  # {"metric": "pipeline_value", "value": 500000000, "currency": "VND"}
    deadline: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="active", nullable=False)  # draft, active, paused, completed, cancelled

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    plans = relationship("AgentPlan", back_populates="goal", cascade="all, delete-orphan")


class AgentPlan(SnowflakeIDMixin, Base):
    """Decomposed execution plan for achieving a goal."""
    __tablename__ = "agent_plans"

    goal_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("agent_goals.id"), index=True, nullable=False)
    workspace_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("workspaces.id"), index=True, nullable=False)
    company_id: Mapped[Optional[int]] = mapped_column(BigInteger, index=True, nullable=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), index=True, nullable=False)

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    rationale: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="draft", nullable=False)  # draft, approved, in_progress, completed, failed
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    goal = relationship("AgentGoal", back_populates="plans")
    steps = relationship("AgentPlanStep", back_populates="plan", cascade="all, delete-orphan", order_by="AgentPlanStep.sequence_order")


class AgentPlanStep(SnowflakeIDMixin, Base):
    """Individual atomic step within an agent plan."""
    __tablename__ = "agent_plan_steps"

    plan_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("agent_plans.id"), index=True, nullable=False)
    sequence_order: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    domain: Mapped[str] = mapped_column(String(100), default="founder", nullable=False)  # founder, sales, finance, marketing, legal, learning
    capability: Mapped[str] = mapped_column(String(100), default="reasoning", nullable=False)  # research, reasoning, data, action, communication, evaluation
    tool_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    policy_level: Mapped[str] = mapped_column(String(50), default="L0_READ", nullable=False)  # L0_READ, L1_SUGGEST, L2_DRAFT, L3A_EXECUTE_WITH_APPROVAL, L3_EXECUTE

    input_jsonb: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    expected_output_jsonb: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    output_jsonb: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    dependencies_jsonb: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)  # list of step_id strings

    status: Mapped[str] = mapped_column(String(50), default="pending", nullable=False)  # pending, running, waiting_approval, completed, failed, skipped
    approval_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True, index=True)

    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    plan = relationship("AgentPlan", back_populates="steps")


class AgentMemoryItem(SnowflakeIDMixin, Base):
    """Structured long-term business memory item with provenance tracking."""
    __tablename__ = "agent_business_memories"

    workspace_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("workspaces.id"), index=True, nullable=False)
    company_id: Mapped[Optional[int]] = mapped_column(BigInteger, index=True, nullable=True)
    user_id: Mapped[Optional[int]] = mapped_column(BigInteger, ForeignKey("users.id"), index=True, nullable=True)

    memory_type: Mapped[str] = mapped_column(String(50), nullable=False)  # company_fact, founder_preference, operating_constraint, approved_decision
    domain: Mapped[str] = mapped_column(String(50), default="general", nullable=False)
    key: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    value_jsonb: Mapped[dict] = mapped_column(JSONB, nullable=False)
    provenance_jsonb: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)  # source, run_id, approved_by, timestamp
    status: Mapped[str] = mapped_column(String(50), default="active", nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
