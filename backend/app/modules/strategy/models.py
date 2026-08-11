from datetime import datetime
from typing import Optional

from sqlalchemy import String, Boolean, DateTime, ForeignKey, BigInteger, func, UniqueConstraint, Text, Integer, Numeric, Float
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column, relationship
from pgvector.sqlalchemy import Vector

from app.db.base_class import Base
from app.core.snowflake import generate_snowflake_id

class StrategyCanvas(Base):
    # Đổi tên từ "strategy_profiles" (Phase 2B cũ) sang "strategy_canvases" khi triển
    # khai Strategic Canvas 1-1-3 - cùng một khái niệm (1 container chiến lược theo
    # workspace/brain), chỉ bổ sung name/description/created_by thay vì tạo bảng song
    # song. FK cũ (BscScorecard.strategy_profile_id) vẫn giữ nguyên tên cột, Postgres
    # tự cập nhật theo bảng đổi tên.
    __tablename__ = "strategy_canvases"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    brain_id: Mapped[int] = mapped_column(ForeignKey("brains.id"), index=True)
    name: Mapped[str] = mapped_column(Text)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="draft")
    created_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class StrategyRevision(Base):
    # Immutable revision theo Canvas (Strategic Canvas 1-1-3 §3.1). Không có khái niệm
    # tương đương nào ở Phase 2B cũ - strategy_canvases/context_packs trước đây chỉ có
    # 1 status phẳng, không có revision_no/lifecycle/parent_revision_id.
    __tablename__ = "strategy_revisions"
    __table_args__ = (
        UniqueConstraint('canvas_id', 'revision_no', name='uix_strategy_revision_canvas_no'),
    )
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    canvas_id: Mapped[int] = mapped_column(ForeignKey("strategy_canvases.id"), index=True)
    revision_no: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(50), default="draft")  # draft, in_review, approved, changes_requested, superseded, archived
    parent_revision_id: Mapped[Optional[int]] = mapped_column(ForeignKey("strategy_revisions.id", use_alter=True), nullable=True)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    approved_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    stale_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class StrategyFoundation(Base):
    # 1 Vision, 1 Mission theo revision (§4.1). Không tồn tại ở Phase 2B cũ.
    __tablename__ = "strategy_foundations"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    strategy_revision_id: Mapped[int] = mapped_column(ForeignKey("strategy_revisions.id"), unique=True, index=True)
    vision: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    mission: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="draft")  # draft, approved
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class CoreValue(Base):
    # Đúng 3 slot/foundation (§4.1) - unique(foundation_id, slot_no) + CHECK slot_no
    # 1-3 ở migration đảm bảo không tạo được value thứ 4.
    __tablename__ = "core_values"
    __table_args__ = (
        UniqueConstraint('foundation_id', 'slot_no', name='uix_core_value_foundation_slot'),
    )
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    foundation_id: Mapped[int] = mapped_column(ForeignKey("strategy_foundations.id", ondelete="CASCADE"), index=True)
    slot_no: Mapped[int] = mapped_column(Integer)
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text)
    decision_rule: Mapped[str] = mapped_column(Text)

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
    revision_id: Mapped[Optional[int]] = mapped_column(nullable=True, index=True)
    evidence_id: Mapped[Optional[int]] = mapped_column(ForeignKey("evidence_items.id"), nullable=True, index=True)
    source_type: Mapped[str] = mapped_column(String(50))
    citation_jsonb: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    included_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)

class StrategyAnalysis(Base):
    __tablename__ = "strategy_analyses"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    portfolio_id: Mapped[Optional[int]] = mapped_column(nullable=True, index=True)
    context_pack_id: Mapped[int] = mapped_column(ForeignKey("context_packs.id"), index=True)
    kind: Mapped[str] = mapped_column(String(50)) # PESTEL, SWOT, TOWS
    status: Mapped[str] = mapped_column(String(50), default="draft")
    input_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    output_revision_id: Mapped[Optional[int]] = mapped_column(nullable=True)
    created_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class PestelItem(Base):
    __tablename__ = "pestel_items"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    portfolio_id: Mapped[Optional[int]] = mapped_column(nullable=True, index=True)
    analysis_id: Mapped[int] = mapped_column(ForeignKey("strategy_analyses.id"), index=True)
    factor: Mapped[str] = mapped_column(String(50))
    statement: Mapped[str] = mapped_column(Text)
    impact: Mapped[str] = mapped_column(String(50))
    horizon: Mapped[str] = mapped_column(String(50))
    confidence: Mapped[str] = mapped_column(String(50))
    evidence_status: Mapped[str] = mapped_column(String(50))

class SwotItem(Base):
    __tablename__ = "swot_items"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    portfolio_id: Mapped[Optional[int]] = mapped_column(nullable=True, index=True)
    analysis_id: Mapped[int] = mapped_column(ForeignKey("strategy_analyses.id"), index=True)
    category: Mapped[str] = mapped_column(String(50))
    statement: Mapped[str] = mapped_column(Text)
    impact: Mapped[str] = mapped_column(String(50))
    likelihood: Mapped[str] = mapped_column(String(50))
    confidence: Mapped[str] = mapped_column(String(50))
    evidence_status: Mapped[str] = mapped_column(String(50))

class TowsOption(Base):
    __tablename__ = "tows_options"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    portfolio_id: Mapped[Optional[int]] = mapped_column(nullable=True, index=True)
    analysis_id: Mapped[int] = mapped_column(ForeignKey("strategy_analyses.id"), index=True)
    quadrant: Mapped[str] = mapped_column(String(50))
    title: Mapped[str] = mapped_column(String(255))
    tradeoffs: Mapped[str] = mapped_column(Text)
    expected_impact: Mapped[str] = mapped_column(String(50))
    confidence: Mapped[str] = mapped_column(String(50))
    status: Mapped[str] = mapped_column(String(50), default="draft")


class StrategicDecision(Base):
    __tablename__ = "strategic_decisions"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    brain_id: Mapped[int] = mapped_column(ForeignKey("brains.id"), index=True)
    context_pack_id: Mapped[int] = mapped_column(ForeignKey("context_packs.id"), index=True)
    tows_option_id: Mapped[Optional[int]] = mapped_column(ForeignKey("tows_options.id"), nullable=True)
    decision: Mapped[str] = mapped_column(Text)
    rationale_revision_id: Mapped[Optional[int]] = mapped_column(nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="draft")
    decided_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class Metric(Base):
    __tablename__ = "metrics"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    brain_id: Mapped[int] = mapped_column(ForeignKey("brains.id"), index=True)
    name: Mapped[str] = mapped_column(String(255))
    formula: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    unit: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    baseline_value: Mapped[Optional[float]] = mapped_column(nullable=True)
    target_value: Mapped[Optional[float]] = mapped_column(nullable=True)
    data_source: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    cadence: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class MetricCheckin(Base):
    __tablename__ = "metric_checkins"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    metric_id: Mapped[int] = mapped_column(ForeignKey("metrics.id"), index=True)
    as_of_at: Mapped[datetime] = mapped_column(DateTime)
    value: Mapped[float] = mapped_column()
    source_ref: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    entered_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
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

class OkrCycle(Base):
    __tablename__ = "okr_cycles"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    brain_id: Mapped[int] = mapped_column(ForeignKey("brains.id"), index=True)
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
    status: Mapped[str] = mapped_column(String(50), default="draft")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class OkrLink(Base):
    __tablename__ = "okr_links"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    from_entity_type: Mapped[str] = mapped_column(String(50))
    from_entity_id: Mapped[int] = mapped_column(index=True)
    to_entity_type: Mapped[str] = mapped_column(String(50))
    to_entity_id: Mapped[int] = mapped_column(index=True)
    relation_type: Mapped[str] = mapped_column(String(50))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class Project(Base):
    __tablename__ = "projects"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    brain_id: Mapped[int] = mapped_column(ForeignKey("brains.id"), index=True)
    title: Mapped[str] = mapped_column(String(255))
    phase: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    current_gate: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="active")
    owner_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    project_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # STRATEGIC, NEW_BUSINESS, PRODUCT, GROWTH, OPERATIONAL, TECHNICAL, EXPERIMENT, COMPLIANCE
    strategic_priority: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # P0, P1, P2, etc.
    founder_attention_budget: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # hours/week
    portfolio_id: Mapped[Optional[int]] = mapped_column(nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class Initiative(Base):
    __tablename__ = "initiatives"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    brain_id: Mapped[int] = mapped_column(ForeignKey("brains.id"), index=True)
    project_id: Mapped[Optional[int]] = mapped_column(ForeignKey("projects.id"), nullable=True)
    title: Mapped[str] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(50), default="active")
    owner_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class InitiativeKeyResultLink(Base):
    __tablename__ = "initiative_key_result_links"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    initiative_id: Mapped[int] = mapped_column(ForeignKey("initiatives.id"), index=True)
    key_result_id: Mapped[int] = mapped_column(ForeignKey("key_results.id"), index=True)
    contribution_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class TwelveWeekCycle(Base):
    __tablename__ = "twelve_week_cycles"
    __table_args__ = (
        # §6.2: "twelve_week_cycles: unique (brain_id, start_date)".
        UniqueConstraint('brain_id', 'start_date', name='uix_twelve_week_cycle_brain_start'),
    )
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    brain_id: Mapped[int] = mapped_column(ForeignKey("brains.id"), index=True)
    okr_cycle_id: Mapped[Optional[int]] = mapped_column(ForeignKey("okr_cycles.id"), nullable=True)
    cycle_contract_id: Mapped[Optional[int]] = mapped_column(ForeignKey("cycle_contracts.id", use_alter=True), nullable=True, index=True)
    theme: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    start_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    end_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    commitment_level: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="draft")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class WeeklyPlan(Base):
    __tablename__ = "weekly_plans"
    __table_args__ = (
        # §6.2: "weekly_plans: unique (cycle_id, week_no) với week_no từ 1 đến 12" -
        # thiếu ràng buộc này thì 2 tuần trùng số thứ tự trong cùng 1 cycle vẫn được
        # tạo bình thường, phá vỡ đúng bất biến 12-Week Year.
        UniqueConstraint('cycle_id', 'week_no', name='uix_weekly_plan_cycle_week'),
    )
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    cycle_id: Mapped[int] = mapped_column(ForeignKey("twelve_week_cycles.id"), index=True)
    stage_id: Mapped[Optional[int]] = mapped_column(ForeignKey("cycle_stages.id"), nullable=True, index=True)
    week_no: Mapped[int] = mapped_column()
    start_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
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
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    weekly_plan_id: Mapped[int] = mapped_column(ForeignKey("weekly_plans.id"), index=True)
    initiative_id: Mapped[Optional[int]] = mapped_column(ForeignKey("initiatives.id"), nullable=True)
    title: Mapped[str] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(50), default="todo")
    planned_effort: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    commitment_owner_type: Mapped[Optional[str]] = mapped_column(String(50), default="FOUNDER")  # FOUNDER, AI_AGENT, CORE_TEAM
    execution_mode: Mapped[Optional[str]] = mapped_column(String(50), default="MANUAL")  # MANUAL, AI_ASSISTED, AUTONOMOUS
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


# ==========================================
# mCOSA V12 — Project Intelligence & 12WY Additions
# ==========================================

class ProjectClassification(Base):
    __tablename__ = "project_classifications"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    project_type: Mapped[str] = mapped_column(String(50))  # STRATEGIC, NEW_BUSINESS, PRODUCT, GROWTH, OPERATIONAL, TECHNICAL, EXPERIMENT, COMPLIANCE
    strategic_depth: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # high, medium, low
    uncertainty_level: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # high, medium, low
    risk_level: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # high, medium, low
    research_required: Mapped[bool] = mapped_column(Boolean, default=False)
    external_evidence_required: Mapped[bool] = mapped_column(Boolean, default=False)
    internal_context_required: Mapped[bool] = mapped_column(Boolean, default=False)
    recommended_methodologies: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    human_required_areas: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    rationale: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    confidence_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    classified_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class MethodologyPlan(Base):
    __tablename__ = "methodology_plans"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    selected_methodologies: Mapped[dict] = mapped_column(JSONB)  # list of selected primitives
    rationale: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="draft")  # draft, approved, active, archived
    custom_rules: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    created_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class CycleContract(Base):
    __tablename__ = "cycle_contracts"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    cycle_id: Mapped[int] = mapped_column(ForeignKey("twelve_week_cycles.id", ondelete="CASCADE"), unique=True, index=True)
    success_definition: Mapped[str] = mapped_column(Text)
    goal_ids: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    kr_ids: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    founder_capacity_per_week: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # hours/week
    reserved_buffer_percent: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # e.g. 20.0
    ai_budget: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    operating_budget: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    risk_constraints: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="draft")  # draft, approved, active
    approved_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class CycleStage(Base):
    __tablename__ = "cycle_stages"
    __table_args__ = (
        UniqueConstraint('cycle_id', 'order_no', name='uix_cycle_stage_cycle_order'),
    )
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    cycle_id: Mapped[int] = mapped_column(ForeignKey("twelve_week_cycles.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(100))  # Discovery, Validation, MVP, Beta, Acquisition, Closing, Week 13 Review
    purpose: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    start_week: Mapped[int] = mapped_column(Integer)
    end_week: Mapped[int] = mapped_column(Integer)
    order_no: Mapped[int] = mapped_column(Integer, default=1)
    expected_outcomes: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="pending")  # pending, in_progress, completed, skipped
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Milestone(Base):
    __tablename__ = "milestones"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    project_id: Mapped[Optional[int]] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=True, index=True)
    cycle_id: Mapped[Optional[int]] = mapped_column(ForeignKey("twelve_week_cycles.id", ondelete="CASCADE"), nullable=True, index=True)
    stage_id: Mapped[Optional[int]] = mapped_column(ForeignKey("cycle_stages.id", ondelete="SET NULL"), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    due_week: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    due_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    required_artifacts: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    required_metrics: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    acceptance_criteria: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="pending")  # pending, in_progress, met, missed, cancelled
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

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

class GateDecision(Base):
    __tablename__ = "gate_decisions"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    milestone_id: Mapped[Optional[int]] = mapped_column(ForeignKey("milestones.id", ondelete="SET NULL"), nullable=True, index=True)
    stage_id: Mapped[Optional[int]] = mapped_column(ForeignKey("cycle_stages.id", ondelete="SET NULL"), nullable=True, index=True)
    decision: Mapped[str] = mapped_column(String(50))  # GO, ITERATE, HOLD, STOP, PIVOT
    rationale: Mapped[str] = mapped_column(Text)
    evidence_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    evidence_refs: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    next_step_instructions: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    decided_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    decided_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class AnalysisImport(Base):
    __tablename__ = "analysis_imports"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    project_id: Mapped[Optional[int]] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=True, index=True)
    strategy_revision_id: Mapped[Optional[int]] = mapped_column(ForeignKey("strategy_revisions.id", ondelete="SET NULL"), nullable=True, index=True)
    raw_input: Mapped[str] = mapped_column(Text)
    parsed_json: Mapped[dict] = mapped_column(JSONB)
    schema_version: Mapped[str] = mapped_column(String(50), default="1.0")
    imported_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

# ==========================================
# Retrieval and AI Router (Phase 3) & Prompt Templates
# ==========================================

class PromptTemplate(Base):
    __tablename__ = "prompt_templates"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[Optional[int]] = mapped_column(ForeignKey("workspaces.id"), nullable=True, index=True)
    brain_id: Mapped[Optional[int]] = mapped_column(ForeignKey("brains.id"), nullable=True, index=True)
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

class WeeklyReview(Base):
    """Bản đánh giá tuần (Weekly Review - Spec §17).

    Ghi nhận bằng chứng đã học, giả định được xác nhận/bác bỏ, và khuyến nghị hành động.
    """
    __tablename__ = "weekly_reviews"
    __table_args__ = (
        UniqueConstraint("weekly_plan_id", name="uix_weekly_review_plan"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    cycle_id: Mapped[int] = mapped_column(ForeignKey("twelve_week_cycles.id"), index=True)
    weekly_plan_id: Mapped[int] = mapped_column(ForeignKey("weekly_plans.id"), index=True)
    week_no: Mapped[int] = mapped_column()
    execution_score: Mapped[float] = mapped_column(Float, default=0.0)
    outcome_score: Mapped[float] = mapped_column(Float, default=0.0)
    evidence_learned: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    assumptions_confirmed: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    assumptions_invalidated: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    recommendation: Mapped[str] = mapped_column(String(50), default="CONTINUE")  # CONTINUE, PIVOT_NEXT_WEEK, DOUBLE_DOWN, RECALIBRATE_CAPACITY
    narrative_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    reviewed_by: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    reviewed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class CycleReview(Base):
    """Bản tổng kết chu kỳ 12 tuần (Cycle Retrospective & Review - Spec §18)."""
    __tablename__ = "cycle_reviews"
    __table_args__ = (
        UniqueConstraint("cycle_id", name="uix_cycle_review_cycle"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    cycle_id: Mapped[int] = mapped_column(ForeignKey("twelve_week_cycles.id"), index=True)
    overall_execution_score: Mapped[float] = mapped_column(Float, default=0.0)
    overall_outcome_score: Mapped[float] = mapped_column(Float, default=0.0)
    okr_achievement_rate: Mapped[float] = mapped_column(Float, default=0.0)
    strategic_learnings: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    systemic_blockers: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    portfolio_adjustments: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    next_cycle_recommendations: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="finalized")
    reviewed_by: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    reviewed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class CelebrationRecord(Base):
    """Ghi nhận lễ kỷ niệm & vinh danh thành tựu chu kỳ (Week 13 Celebration - Spec §19)."""
    __tablename__ = "celebration_records"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    cycle_id: Mapped[int] = mapped_column(ForeignKey("twelve_week_cycles.id"), index=True)
    title: Mapped[str] = mapped_column(String(255))
    milestones_achieved: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    top_performers_recognized: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    rewards_or_rituals: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    reflection_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    celebrated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


# ==========================================
# mCOSA V12 — Portfolio Intelligence (Sprint 6)
# ==========================================

class Portfolio(Base):
    """Mô hình Portfolio - Danh mục quản lý nhiều dự án chiến lược (§21–23)."""
    __tablename__ = "portfolios"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    brain_id: Mapped[Optional[int]] = mapped_column(ForeignKey("brains.id"), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    strategic_focus: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="active")  # active, archived, draft
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class PortfolioProject(Base):
    """Liên kết Dự án vào Danh mục với phân bổ năng lực & độ ưu tiên chiến lược (§23)."""
    __tablename__ = "portfolio_projects"
    __table_args__ = (
        UniqueConstraint("portfolio_id", "project_id", name="uix_portfolio_project"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    portfolio_id: Mapped[int] = mapped_column(ForeignKey("portfolios.id", ondelete="CASCADE"), index=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    strategic_priority: Mapped[str] = mapped_column(String(50), default="core")  # core, growth, experimental, maintenance
    capacity_allocation: Mapped[float] = mapped_column(Float, default=0.0)  # 0.0 - 100.0%
    founder_attention_hours: Mapped[float] = mapped_column(Float, default=0.0)  # hours/week
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ProjectPestelImpact(Base):
    """Ma trận tác động PESTEL lên từng Dự án trong Danh mục (Project PESTEL Impact Matrix - Spec §24)."""
    __tablename__ = "project_pestel_impacts"
    __table_args__ = (
        UniqueConstraint("project_id", "pestel_item_id", name="uix_project_pestel_impact"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    pestel_item_id: Mapped[int] = mapped_column(ForeignKey("pestel_items.id", ondelete="CASCADE"), index=True)
    impact_type: Mapped[str] = mapped_column(String(50), default="POSITIVE")  # POSITIVE, NEGATIVE, NEUTRAL
    impact_magnitude: Mapped[str] = mapped_column(String(50), default="MEDIUM")  # HIGH, MEDIUM, LOW
    impact_analysis: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    mitigation_or_leverage: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


# ==========================================
# mCOSA V12 — Portfolio SWOT, Options & Synergies (Sprint 7)
# ==========================================

class PortfolioSynergy(Base):
    """Cộng hưởng giá trị giữa các dự án trong Danh mục (Spec §25)."""
    __tablename__ = "portfolio_synergies"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    portfolio_id: Mapped[int] = mapped_column(ForeignKey("portfolios.id", ondelete="CASCADE"), index=True)
    source_project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    target_project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    synergy_type: Mapped[str] = mapped_column(String(50), default="SHARED_CAPABILITY")  # REVENUE, COST_SAVING, SHARED_CAPABILITY, DATA_NETWORK
    description: Mapped[str] = mapped_column(Text)
    estimated_value: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="identified")  # identified, active, realized
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class PortfolioDependency(Base):
    """Quan hệ phụ thuộc giữa các dự án trong Danh mục (Spec §26)."""
    __tablename__ = "portfolio_dependencies"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    portfolio_id: Mapped[int] = mapped_column(ForeignKey("portfolios.id", ondelete="CASCADE"), index=True)
    predecessor_project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    successor_project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    dependency_type: Mapped[str] = mapped_column(String(50), default="BLOCKS")  # BLOCKS, ENABLES, REQUIRES_MILESTONE
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class PortfolioOption(Base):
    """Tùy chọn chiến lược cấp Danh mục (Portfolio Strategic Options - Spec §27)."""
    __tablename__ = "portfolio_options"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    portfolio_id: Mapped[int] = mapped_column(ForeignKey("portfolios.id", ondelete="CASCADE"), index=True)
    tows_option_id: Mapped[Optional[int]] = mapped_column(ForeignKey("tows_options.id", ondelete="SET NULL"), nullable=True)
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    strategic_fit_score: Mapped[float] = mapped_column(Float, default=0.8)  # 0.0 - 1.0
    feasibility_score: Mapped[float] = mapped_column(Float, default=0.7)  # 0.0 - 1.0
    risk_level: Mapped[str] = mapped_column(String(50), default="MEDIUM")  # LOW, MEDIUM, HIGH
    status: Mapped[str] = mapped_column(String(50), default="draft")  # draft, under_review, selected, rejected
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


# ==========================================
# mCOSA V12 — Portfolio Cycles, WIP Limit & Capacity (Sprint 8)
# ==========================================

class FounderProfile(Base):
    """Hồ sơ năng lực & giới hạn WIP của Founder (Spec §31)."""
    __tablename__ = "founder_profiles"
    __table_args__ = (
        UniqueConstraint("workspace_id", "user_id", name="uix_founder_profile_workspace_user"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    weekly_capacity_hours: Mapped[float] = mapped_column(Float, default=40.0)
    max_active_strategic_projects: Mapped[int] = mapped_column(Integer, default=3)  # WIP Limit §31
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class PortfolioCycle(Base):
    """Chu kỳ 12 tuần cấp Danh mục (Portfolio 12WY Cycle - Spec §28–30)."""
    __tablename__ = "portfolio_cycles"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    portfolio_id: Mapped[int] = mapped_column(ForeignKey("portfolios.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(50), default="draft")  # draft, active, completed, archived
    start_date: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    end_date: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    active_project_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class CapacityAllocation(Base):
    """Phân bổ công suất đội ngũ cho các dự án trong chu kỳ danh mục."""
    __tablename__ = "capacity_allocations"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    portfolio_cycle_id: Mapped[int] = mapped_column(ForeignKey("portfolio_cycles.id", ondelete="CASCADE"), index=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    allocated_percentage: Mapped[float] = mapped_column(Float, default=0.0)  # 0.0 - 100.0%
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class FounderAttentionAllocation(Base):
    """Phân bổ thời gian tập trung hàng tuần của Founder cho các dự án."""
    __tablename__ = "founder_attention_allocations"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    portfolio_cycle_id: Mapped[int] = mapped_column(ForeignKey("portfolio_cycles.id", ondelete="CASCADE"), index=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    allocated_hours_per_week: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


# ==========================================
# mCOSA V12 — Next Best Action Engine (Sprint 9 Spec §37 & V12.6)
# ==========================================

class NextActionCandidate(Base):
    """Ứng viên hành động tiếp theo tốt nhất cho CEO / Founder (Spec §37)."""
    __tablename__ = "next_action_candidates"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    project_id: Mapped[Optional[int]] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=True, index=True)
    portfolio_id: Mapped[Optional[int]] = mapped_column(ForeignKey("portfolios.id", ondelete="CASCADE"), nullable=True, index=True)
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    category: Mapped[str] = mapped_column(String(50), default="GOVERNANCE_DECISION")  # STAGE_GATE_REVIEW, WEEKLY_MISSION, PESTEL_MITIGATION, GOVERNANCE_DECISION, STRATEGIC_ALIGNMENT
    urgency_score: Mapped[float] = mapped_column(Float, default=0.5)  # 0.0 - 1.0
    impact_score: Mapped[float] = mapped_column(Float, default=0.5)  # 0.0 - 1.0
    effort_score: Mapped[float] = mapped_column(Float, default=0.5)  # 0.0 - 1.0
    r0_score: Mapped[float] = mapped_column(Float, default=0.5)  # Deterministic weighted formula §37
    status: Mapped[str] = mapped_column(String(50), default="proposed")  # proposed, accepted, dismissed, executed
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class NextActionRanking(Base):
    """Kết quả xếp hạng danh sách Next Best Action theo các vòng R0, R1, R2."""
    __tablename__ = "next_action_rankings"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    candidate_id: Mapped[int] = mapped_column(ForeignKey("next_action_candidates.id", ondelete="CASCADE"), index=True)
    ranking_round: Mapped[str] = mapped_column(String(50), default="R0_DETERMINISTIC")  # R0_DETERMINISTIC, R1_RULES, R2_AI_TERRA
    rank_position: Mapped[int] = mapped_column(Integer, default=1)
    composite_score: Mapped[float] = mapped_column(Float, default=0.5)
    reasoning: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


# ==========================================
# mCOSA V12 — Living PESTEL & Model Audit (Sprint 10 Spec §48 & V12.7)
# ==========================================

class PestelSignal(Base):
    """Tín hiệu vĩ mô Living PESTEL (Spec §48)."""
    __tablename__ = "pestel_signals"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    signal_title: Mapped[str] = mapped_column(String(255))
    signal_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    pestel_category: Mapped[str] = mapped_column(String(50), default="ECONOMIC")  # POLITICAL, ECONOMIC, SOCIAL, TECHNOLOGICAL, ENVIRONMENTAL, LEGAL
    magnitude: Mapped[str] = mapped_column(String(50), default="MEDIUM")  # LOW, MEDIUM, HIGH, CRITICAL
    is_material_change: Mapped[bool] = mapped_column(Boolean, default=False)  # True nếu phát hiện thay đổi trọng yếu §48
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
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)











