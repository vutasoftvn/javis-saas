from datetime import datetime
from typing import Optional, Dict, Any, List

from sqlalchemy import String, Boolean, DateTime, ForeignKey, BigInteger, Text, Integer, Float, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base
from app.core.snowflake import generate_snowflake_id

class MarketingContext(Base):
    __tablename__ = "marketing_contexts"
    
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    brain_id: Mapped[int] = mapped_column(ForeignKey("brains.id"), index=True)
    strategy_revision_id: Mapped[Optional[int]] = mapped_column(ForeignKey("strategy_revisions.id"), nullable=True, index=True)
    
    market: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    category: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    icp: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    personas: Mapped[Optional[List[Dict[str, Any]]]] = mapped_column(JSONB, nullable=True)
    jobs_to_be_done: Mapped[Optional[List[str]]] = mapped_column(JSONB, nullable=True)
    positioning: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    value_proposition: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    brand_voice: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    competitors: Mapped[Optional[List[Dict[str, Any]]]] = mapped_column(JSONB, nullable=True)
    pricing: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    constraints: Mapped[Optional[List[str]]] = mapped_column(JSONB, nullable=True)
    customer_research: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    product_marketing: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    offer_architecture: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    marketing_plan_12w: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    proofs: Mapped[Optional[List[Dict[str, Any]]]] = mapped_column(JSONB, nullable=True)
    channels: Mapped[Optional[List[str]]] = mapped_column(JSONB, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class MarketingObjective(Base):
    __tablename__ = "marketing_objectives"
    
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    brain_id: Mapped[int] = mapped_column(ForeignKey("brains.id"), index=True)
    strategic_objective_id: Mapped[Optional[int]] = mapped_column(ForeignKey("strategic_objectives.id"), nullable=True, index=True)
    
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    target_metric: Mapped[str] = mapped_column(String(100))
    target_value: Mapped[float] = mapped_column(Float)
    current_value: Mapped[float] = mapped_column(Float, default=0.0)
    unit: Mapped[str] = mapped_column(String(50), default="count")
    status: Mapped[str] = mapped_column(String(50), default="active")  # active, completed, cancelled
    period_weeks: Mapped[int] = mapped_column(Integer, default=12)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class MarketingCampaign(Base):
    __tablename__ = "marketing_campaigns"
    
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    brain_id: Mapped[int] = mapped_column(ForeignKey("brains.id"), index=True)
    marketing_objective_id: Mapped[Optional[int]] = mapped_column(ForeignKey("marketing_objectives.id"), nullable=True, index=True)
    
    name: Mapped[str] = mapped_column(String(255))
    funnel_stage: Mapped[str] = mapped_column(String(50), default="discover")  # discover, engage, consider, convert, retain
    channels: Mapped[List[str]] = mapped_column(JSONB, default=list)
    budget: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[str] = mapped_column(String(50), default="draft")  # draft, pending_approval, active, paused, completed
    owner: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    start_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    end_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class CampaignAsset(Base):
    __tablename__ = "campaign_assets"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    campaign_id: Mapped[int] = mapped_column(ForeignKey("marketing_campaigns.id", ondelete="CASCADE"), index=True)
    # Asset phải mang workspace_id riêng: mọi endpoint đọc/ghi asset theo asset_id đều
    # lọc trực tiếp theo workspace đã xác thực thay vì tin campaign_id client gửi lên.
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)

    asset_type: Mapped[str] = mapped_column(String(50))  # copy, email, landing_page, ad_creative, social_post
    title: Mapped[str] = mapped_column(String(255))
    content: Mapped[str] = mapped_column(Text)
    meta_data: Mapped[Optional[Dict[str, Any]]] = mapped_column("metadata", JSONB, nullable=True)
    approval_status: Mapped[str] = mapped_column("status", String(50), default="draft")  # draft, pending_approval, approved, rejected

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class MarketingMetric(Base):
    """Chỉ số marketing hiện tại (§13). Mỗi (workspace, brain, metric_name) giữ một dòng
    'giá trị hiện tại'; lịch sử nằm ở metric_snapshots để vẽ xu hướng."""
    __tablename__ = "marketing_metrics"
    __table_args__ = (
        UniqueConstraint("workspace_id", "brain_id", "metric_name", name="uq_marketing_metric_scope_name"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    brain_id: Mapped[int] = mapped_column(ForeignKey("brains.id"), index=True)
    campaign_id: Mapped[Optional[int]] = mapped_column(ForeignKey("marketing_campaigns.id"), nullable=True, index=True)

    category: Mapped[str] = mapped_column(String(50), default="acquisition")  # acquisition, conversion, revenue, retention, content
    metric_name: Mapped[str] = mapped_column(String(100), index=True)  # ctr, cpc, cac, mrr, churn, cvr
    current_value: Mapped[float] = mapped_column("metric_value", Float, default=0.0)
    previous_value: Mapped[float] = mapped_column(Float, default=0.0)
    change_pct: Mapped[float] = mapped_column(Float, default=0.0)
    unit: Mapped[str] = mapped_column(String(50), default="number")  # currency, percentage, number
    period: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # daily, weekly, monthly

    recorded_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class MetricSnapshot(Base):
    __tablename__ = "metric_snapshots"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    metric_id: Mapped[Optional[int]] = mapped_column(ForeignKey("marketing_metrics.id", ondelete="CASCADE"), nullable=True, index=True)
    metric_name: Mapped[str] = mapped_column(String(100), index=True)
    value: Mapped[float] = mapped_column(Float)
    recorded_at: Mapped[datetime] = mapped_column("snapshot_at", DateTime, default=datetime.utcnow, index=True)

class MarketingExperiment(Base):
    __tablename__ = "marketing_experiments"
    
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    brain_id: Mapped[int] = mapped_column(ForeignKey("brains.id"), index=True)
    campaign_id: Mapped[Optional[int]] = mapped_column(ForeignKey("marketing_campaigns.id"), nullable=True, index=True)
    
    hypothesis: Mapped[str] = mapped_column(Text)
    metric: Mapped[str] = mapped_column(String(100))
    baseline_value: Mapped[float] = mapped_column(Float, default=0.0)
    target_value: Mapped[float] = mapped_column(Float, default=0.0)
    variant_a: Mapped[str] = mapped_column(Text)
    variant_b: Mapped[str] = mapped_column(Text)
    landing_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    variant_a_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    variant_b_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    sample_size: Mapped[int] = mapped_column(Integer, default=0)
    # draft, running, win, lose, inconclusive, iterate (§15)
    status: Mapped[str] = mapped_column(String(50), default="draft")
    decision: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    learning: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    evaluation: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class MarketingLearning(Base):
    """Learning Loop §16: observation → hypothesis → action → result → learning."""
    __tablename__ = "marketing_learnings"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    brain_id: Mapped[int] = mapped_column(ForeignKey("brains.id"), index=True)
    experiment_id: Mapped[Optional[int]] = mapped_column(ForeignKey("marketing_experiments.id"), nullable=True, index=True)
    campaign_id: Mapped[Optional[int]] = mapped_column(ForeignKey("marketing_campaigns.id"), nullable=True, index=True)

    observation: Mapped[str] = mapped_column(Text)
    hypothesis: Mapped[str] = mapped_column(Text)
    action: Mapped[str] = mapped_column(Text)
    result: Mapped[str] = mapped_column(Text)
    learning: Mapped[str] = mapped_column("insight", Text)
    category: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    confidence: Mapped[str] = mapped_column(String(50), default="medium")  # high, medium, low
    impact_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    reusable_rule: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class SkillExecution(Base):
    """§25 Skill Evaluation: mỗi lần chạy capability đều ghi lại để chấm điểm provider
    và phục vụ audit. Không có bảng này thì router không bao giờ tự chọn được provider tốt hơn."""
    __tablename__ = "skill_executions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    brain_id: Mapped[int] = mapped_column(ForeignKey("brains.id"), index=True)
    approval_id: Mapped[Optional[int]] = mapped_column(ForeignKey("pending_approvals.id"), nullable=True, index=True)

    capability_id: Mapped[str] = mapped_column(String(100), index=True)
    provider: Mapped[Dict[str, Any]] = mapped_column(JSONB)
    task_input: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict)
    output: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    # simulated: đã qua kernel nhưng chưa có runtime provider thật (Phase 2).
    # executed / failed / rejected: khi runtime đã gắn.
    status: Mapped[str] = mapped_column(String(50), default="simulated")
    requested_by_agent: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    latency_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    cost: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    human_rating: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class SkillRegistry(Base):
    __tablename__ = "skill_registries"
    
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    capability_id: Mapped[str] = mapped_column(String(100), index=True)  # marketing.copywriting, marketing.cro, marketing.aeo
    
    primary_provider: Mapped[Dict[str, Any]] = mapped_column(JSONB)
    fallback_provider: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    permissions: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict)
    quality_gate: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict)
    
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class PendingApproval(Base):
    __tablename__ = "pending_approvals"
    
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    brain_id: Mapped[int] = mapped_column(ForeignKey("brains.id"), index=True)
    
    action_type: Mapped[str] = mapped_column(String(100))  # publish_content, spend_budget, change_pricing, pause_campaign
    title: Mapped[str] = mapped_column(String(255))
    details: Mapped[Dict[str, Any]] = mapped_column(JSONB)
    status: Mapped[str] = mapped_column(String(50), default="pending")  # pending, approved, rejected
    requested_by_agent: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    reviewed_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    review_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class MarketingLoop(Base):
    """§18 Marketing Loops: Content Loop, Paid Ads Loop, Conversion Loop, Retention Loop."""
    __tablename__ = "marketing_loops"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    brain_id: Mapped[int] = mapped_column(ForeignKey("brains.id"), index=True)

    loop_type: Mapped[str] = mapped_column(String(50), index=True)  # content, paid_ads, conversion, retention
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="active")  # active, paused, draft
    current_step: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    loop_config: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict)
    metrics_summary: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    last_run_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class MarketingDecision(Base):
    """§53 Decision Journal: Context, Decision, Reason, Alternatives, Expected Outcome, Review Date, Actual Outcome, Learning."""
    __tablename__ = "marketing_decisions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    brain_id: Mapped[int] = mapped_column(ForeignKey("brains.id"), index=True)
    campaign_id: Mapped[Optional[int]] = mapped_column(ForeignKey("marketing_campaigns.id"), nullable=True, index=True)

    title: Mapped[str] = mapped_column(String(255))
    context_summary: Mapped[str] = mapped_column(Text)
    decision: Mapped[str] = mapped_column(Text)
    reason: Mapped[str] = mapped_column(Text)
    alternatives: Mapped[Optional[List[str]]] = mapped_column(JSONB, nullable=True)
    expected_outcome: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    review_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    actual_outcome: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    learning: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class MarketingRecommendation(Base):
    """§52 Recommendation Model: problem, evidence, hypothesis, recommended_action, expected_impact, confidence, cost, risk, approval."""
    __tablename__ = "marketing_recommendations"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    brain_id: Mapped[int] = mapped_column(ForeignKey("brains.id"), index=True)
    approval_id: Mapped[Optional[int]] = mapped_column(ForeignKey("pending_approvals.id"), nullable=True, index=True)

    title: Mapped[str] = mapped_column(String(255))
    problem: Mapped[str] = mapped_column(Text)
    evidence: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    hypothesis: Mapped[str] = mapped_column(Text)
    recommended_action: Mapped[str] = mapped_column(Text)
    expected_impact: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    confidence: Mapped[str] = mapped_column(String(50), default="medium")  # high, medium, low
    estimated_cost: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    risk_level: Mapped[str] = mapped_column(String(50), default="low")  # low, medium, high
    status: Mapped[str] = mapped_column(String(50), default="open")  # open, accepted, rejected, implemented

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

