from datetime import datetime
from typing import Optional, List

from sqlalchemy import String, Boolean, DateTime, ForeignKey, BigInteger, func, UniqueConstraint, Text, Integer, Numeric, Float, Index, text
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column, relationship, object_session
from pgvector.sqlalchemy import Vector

from db.base_class import Base
from core.snowflake import generate_snowflake_id

class TwelveWeekCycle(Base):
    __tablename__ = "twelve_week_cycles"
    __table_args__ = (
        # §6.2: "twelve_week_cycles: unique (brain_id, start_date)".
        UniqueConstraint('brain_id', 'start_date', name='uix_twelve_week_cycle_brain_start'),
        Index("ix_twelve_week_cycle_mvp_stage_id", "mvp_stage_id"),
        Index("ix_twelve_week_cycle_project_id", "project_id"),
        {"schema": "operating"},
    )
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("core.workspaces.id"), index=True)
    brain_id: Mapped[int] = mapped_column(ForeignKey("knowledge.brains.id"), index=True)
    project_id: Mapped[Optional[int]] = mapped_column(ForeignKey("strategy.projects.id"), nullable=True, index=True)
    # References MvpStage, not the unrelated CycleStage - see WeeklyPlan.stage_id.
    mvp_stage_id: Mapped[Optional[int]] = mapped_column(ForeignKey("strategy.mvp_stages.id"), nullable=True)
    okr_cycle_id: Mapped[Optional[int]] = mapped_column(ForeignKey("strategy.okr_cycles.id"), nullable=True)
    cycle_contract_id: Mapped[Optional[int]] = mapped_column(ForeignKey("operating.cycle_contracts.id", use_alter=True), nullable=True, index=True)
    theme: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    vision_statement: Mapped[str] = mapped_column(Text, default="")
    stage_at_start: Mapped[str] = mapped_column(String(50), default="S1_PROBLEM_VALIDATION")
    current_week: Mapped[int] = mapped_column(Integer, default=1)
    duration_weeks: Mapped[int] = mapped_column(Integer, default=12)
    overall_execution_score: Mapped[float] = mapped_column(Float, default=0.0)
    start_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    end_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    commitment_level: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="ACTIVE")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class WeeklyPlan(Base):
    __tablename__ = "weekly_plans"
    __table_args__ = (
        # §6.2: "weekly_plans: unique (cycle_id, week_no) với week_no từ 1 đến 12" -
        # thiếu ràng buộc này thì 2 tuần trùng số thứ tự trong cùng 1 cycle vẫn được
        # tạo bình thường, phá vỡ đúng bất biến 12-Week Year.
        UniqueConstraint('cycle_id', 'week_no', name='uix_weekly_plan_cycle_week'),
        {"schema": "operating"},
    )
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("core.workspaces.id"), index=True)
    cycle_id: Mapped[int] = mapped_column(ForeignKey("operating.twelve_week_cycles.id"), index=True)
    stage_id: Mapped[Optional[int]] = mapped_column(ForeignKey("operating.cycle_stages.id"), nullable=True, index=True)
    week_no: Mapped[int] = mapped_column()
    start_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    end_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    focus: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    mission: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    success_criteria: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    execution_score: Mapped[Optional[float]] = mapped_column(nullable=True)
    outcome_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    blockers_jsonb: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    reflection: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class WeeklyCommitment(Base):
    __tablename__ = "weekly_commitments"
    __table_args__ = {"schema": "operating"}
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("core.workspaces.id"), index=True)
    weekly_plan_id: Mapped[int] = mapped_column(ForeignKey("operating.weekly_plans.id"), index=True)
    initiative_id: Mapped[Optional[int]] = mapped_column(ForeignKey("strategy.initiatives.id"), nullable=True)
    title: Mapped[str] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(50), default="todo")
    planned_effort: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    commitment_owner_type: Mapped[Optional[str]] = mapped_column(String(50), default="FOUNDER")  # FOUNDER, AI_AGENT, CORE_TEAM
    execution_mode: Mapped[Optional[str]] = mapped_column(String(50), default="MANUAL")  # MANUAL, AI_ASSISTED, AUTONOMOUS
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


# ==========================================
# mCOSA V12 — Project Intelligence & 12WY Additions
# ==========================================

class CycleContract(Base):
    __tablename__ = "cycle_contracts"
    __table_args__ = {"schema": "operating"}
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("core.workspaces.id"), index=True)
    cycle_id: Mapped[int] = mapped_column(ForeignKey("operating.twelve_week_cycles.id", ondelete="CASCADE"), unique=True, index=True)
    success_definition: Mapped[str] = mapped_column(Text)
    goal_ids: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    kr_ids: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    founder_capacity_per_week: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # hours/week
    reserved_buffer_percent: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # e.g. 20.0
    ai_budget: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    operating_budget: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    risk_constraints: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="draft")  # draft, approved, active
    approved_by: Mapped[Optional[int]] = mapped_column(ForeignKey("core.users.id"), nullable=True)
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class CycleStage(Base):
    __tablename__ = "cycle_stages"
    __table_args__ = (
        UniqueConstraint('cycle_id', 'order_no', name='uix_cycle_stage_cycle_order'),
        {"schema": "operating"},
    )
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("core.workspaces.id"), index=True)
    cycle_id: Mapped[int] = mapped_column(ForeignKey("operating.twelve_week_cycles.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(100))  # Discovery, Validation, MVP, Beta, Acquisition, Closing, Week 13 Review
    purpose: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    start_week: Mapped[int] = mapped_column(Integer)
    end_week: Mapped[int] = mapped_column(Integer)
    order_no: Mapped[int] = mapped_column(Integer, default=1)
    expected_outcomes: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="pending")  # pending, in_progress, completed, skipped
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class WeeklyReview(Base):
    """Bản đánh giá tuần (Weekly Review - Spec §17).

    Ghi nhận bằng chứng đã học, giả định được xác nhận/bác bỏ, và khuyến nghị hành động.
    """
    __tablename__ = "weekly_reviews"
    __table_args__ = (
        UniqueConstraint("weekly_plan_id", name="uix_weekly_review_plan"),
        {"schema": "operating"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("core.workspaces.id"), index=True)
    cycle_id: Mapped[int] = mapped_column(ForeignKey("operating.twelve_week_cycles.id"), index=True)
    weekly_plan_id: Mapped[int] = mapped_column(ForeignKey("operating.weekly_plans.id"), index=True)
    week_no: Mapped[int] = mapped_column()
    execution_score: Mapped[float] = mapped_column(Float, default=0.0)
    outcome_score: Mapped[float] = mapped_column(Float, default=0.0)
    evidence_learned: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    assumptions_confirmed: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    assumptions_invalidated: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    recommendation: Mapped[str] = mapped_column(String(50), default="CONTINUE")  # CONTINUE, PIVOT_NEXT_WEEK, DOUBLE_DOWN, RECALIBRATE_CAPACITY
    narrative_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    reviewed_by: Mapped[int] = mapped_column(ForeignKey("core.users.id"), index=True)
    reviewed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class CycleReview(Base):
    """Bản tổng kết chu kỳ 12 tuần (Cycle Retrospective & Review - Spec §18)."""
    __tablename__ = "cycle_reviews"
    __table_args__ = (
        UniqueConstraint("cycle_id", name="uix_cycle_review_cycle"),
        {"schema": "operating"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("core.workspaces.id"), index=True)
    cycle_id: Mapped[int] = mapped_column(ForeignKey("operating.twelve_week_cycles.id"), index=True)
    overall_execution_score: Mapped[float] = mapped_column(Float, default=0.0)
    overall_outcome_score: Mapped[float] = mapped_column(Float, default=0.0)
    okr_achievement_rate: Mapped[float] = mapped_column(Float, default=0.0)
    strategic_learnings: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    systemic_blockers: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    portfolio_adjustments: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    next_cycle_recommendations: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="finalized")
    reviewed_by: Mapped[int] = mapped_column(ForeignKey("core.users.id"), index=True)
    reviewed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class CelebrationRecord(Base):
    """Ghi nhận lễ kỷ niệm & vinh danh thành tựu chu kỳ (Week 13 Celebration - Spec §19)."""
    __tablename__ = "celebration_records"
    __table_args__ = {"schema": "operating"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("core.workspaces.id"), index=True)
    cycle_id: Mapped[int] = mapped_column(ForeignKey("operating.twelve_week_cycles.id"), index=True)
    title: Mapped[str] = mapped_column(String(255))
    milestones_achieved: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    top_performers_recognized: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    rewards_or_rituals: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    reflection_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_by: Mapped[int] = mapped_column(ForeignKey("core.users.id"), index=True)
    celebrated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


# ==========================================
# mCOSA V12 — Portfolio Intelligence (Sprint 6)
# ==========================================

class TacticalExecutionItem(Base):
    """Hành động chiến thuật tuần & Chỉ số dẫn dắt (12WY Tactics & Lead Indicators)."""
    __tablename__ = "tactical_execution_items"
    __table_args__ = {"schema": "operating"}
    
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("core.workspaces.id"), index=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("strategy.projects.id"), index=True)
    cycle_id: Mapped[int] = mapped_column(ForeignKey("operating.twelve_week_cycles.id"), index=True)
    
    week_number: Mapped[int] = mapped_column(Integer, index=True) # 1 -> 12
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text, default="")
    
    tows_option_id: Mapped[Optional[int]] = mapped_column(ForeignKey("strategy.tows_options.id"), nullable=True)
    hypothesis_id: Mapped[Optional[int]] = mapped_column(ForeignKey("strategy.hypotheses.id"), nullable=True)
    
    lead_indicator_name: Mapped[str] = mapped_column(String(255))
    target_count: Mapped[int] = mapped_column(Integer, default=1)
    actual_count: Mapped[int] = mapped_column(Integer, default=0)
    
    status: Mapped[str] = mapped_column(String(50), default="PLANNED") # PLANNED | IN_PROGRESS | DONE | BLOCKED
    owner_role: Mapped[str] = mapped_column(String(100), default="Founder")
    
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class WeeklyAccountabilityReview(Base):
    """Nhật ký phiên kiểm điểm tiến độ tuần (Weekly Accountability Meeting - WAM)."""
    __tablename__ = "weekly_accountability_reviews"
    __table_args__ = {"schema": "operating"}
    
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("core.workspaces.id"), index=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("strategy.projects.id"), index=True)
    cycle_id: Mapped[int] = mapped_column(ForeignKey("operating.twelve_week_cycles.id"), index=True)
    
    week_number: Mapped[int] = mapped_column(Integer)
    execution_score: Mapped[float] = mapped_column(Float, default=0.0)
    
    total_planned: Mapped[int] = mapped_column(Integer, default=0)
    total_completed: Mapped[int] = mapped_column(Integer, default=0)
    
    key_breakthroughs: Mapped[dict] = mapped_column(JSONB, default=list)
    root_cause_blocks: Mapped[dict] = mapped_column(JSONB, default=list)
    ai_recommendations: Mapped[dict] = mapped_column(JSONB, default=list)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
