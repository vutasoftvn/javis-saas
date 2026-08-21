from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, field_validator
from business.marketing.services.funnel_engine import FunnelEngine

CAMPAIGN_STATUSES = {"draft", "pending_approval", "active", "paused", "completed"}
CAMPAIGN_STATUSES_REQUIRING_APPROVAL = {"active", "paused"}
EXPERIMENT_DECISIONS = {"WIN", "LOSE", "INCONCLUSIVE", "ITERATE"}
METRIC_CATEGORIES = {"acquisition", "conversion", "revenue", "retention", "content"}
LOOP_TYPES = {"content", "paid_ads", "conversion", "retention"}


class MarketingContextCreate(BaseModel):
    strategy_revision_id: Optional[int] = None
    market: Optional[Dict[str, Any]] = None
    category: Optional[str] = None
    icp: Optional[Dict[str, Any]] = None
    personas: Optional[List[Dict[str, Any]]] = None
    jobs_to_be_done: Optional[List[str]] = None
    positioning: Optional[Dict[str, Any]] = None
    value_proposition: Optional[Dict[str, Any]] = None
    brand_voice: Optional[Dict[str, Any]] = None
    competitors: Optional[List[Dict[str, Any]]] = None
    pricing: Optional[Dict[str, Any]] = None
    constraints: Optional[List[str]] = None
    customer_research: Optional[Dict[str, Any]] = None
    product_marketing: Optional[Dict[str, Any]] = None
    offer_architecture: Optional[Dict[str, Any]] = None
    marketing_plan_12w: Optional[Dict[str, Any]] = None
    proofs: Optional[List[Dict[str, Any]]] = None
    channels: Optional[List[str]] = None


class CustomerResearchUpdate(BaseModel):
    customer_research: Dict[str, Any]


class ProductMarketingUpdate(BaseModel):
    product_marketing: Dict[str, Any]


class OfferArchitectureUpdate(BaseModel):
    offer_architecture: Dict[str, Any]


class Plan12WUpdate(BaseModel):
    marketing_plan_12w: Dict[str, Any]


class MarketingLoopCreate(BaseModel):
    loop_type: str
    name: str
    description: Optional[str] = None
    loop_config: Dict[str, Any] = Field(default_factory=dict)
    metrics_summary: Optional[Dict[str, Any]] = None

    @field_validator("loop_type")
    @classmethod
    def validate_loop_type(cls, v: str) -> str:
        if v not in LOOP_TYPES:
            raise ValueError(f"loop_type phải thuộc {sorted(LOOP_TYPES)}")
        return v


class MarketingLoopUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    current_step: Optional[str] = None
    loop_config: Optional[Dict[str, Any]] = None
    metrics_summary: Optional[Dict[str, Any]] = None


class AttributionCalculateRequest(BaseModel):
    touchpoints: List[Dict[str, Any]]
    model_type: str = "last_touch"
    conversion_value: float = 1.0


class DecisionCreate(BaseModel):
    title: str
    context_summary: str
    decision: str
    reason: str
    alternatives: Optional[List[str]] = None
    expected_outcome: Optional[str] = None
    campaign_id: Optional[int] = None


class DecisionUpdate(BaseModel):
    actual_outcome: Optional[str] = None
    learning: Optional[str] = None


class RecommendationCreate(BaseModel):
    title: str
    problem: str
    evidence: Optional[Dict[str, Any]] = None
    hypothesis: str
    recommended_action: str
    expected_impact: Optional[str] = None
    confidence: str = "medium"
    estimated_cost: Optional[float] = None
    risk_level: str = "low"


class MarketingObjectiveCreate(BaseModel):
    strategic_objective_id: Optional[int] = None
    title: str
    description: Optional[str] = None
    target_metric: str
    target_value: float
    current_value: float = 0.0
    unit: str = "count"
    period_weeks: int = 12


class MarketingObjectiveUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    target_metric: Optional[str] = None
    target_value: Optional[float] = None
    current_value: Optional[float] = None
    unit: Optional[str] = None
    status: Optional[str] = None


class CampaignCreate(BaseModel):
    marketing_objective_id: Optional[int] = None
    name: str
    funnel_stage: str = "discover"
    channels: List[str] = Field(default_factory=list)
    budget: float = 0.0
    owner: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None

    @field_validator("funnel_stage")
    @classmethod
    def validate_stage(cls, v: str) -> str:
        if not FunnelEngine.is_valid_stage(v):
            raise ValueError(f"funnel_stage phải thuộc {FunnelEngine.STAGE_KEYS}")
        return v


class CampaignUpdate(BaseModel):
    name: Optional[str] = None
    funnel_stage: Optional[str] = None
    channels: Optional[List[str]] = None
    budget: Optional[float] = None
    owner: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None

    @field_validator("funnel_stage")
    @classmethod
    def validate_stage(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not FunnelEngine.is_valid_stage(v):
            raise ValueError(f"funnel_stage phải thuộc {FunnelEngine.STAGE_KEYS}")
        return v


class CampaignStatusUpdate(BaseModel):
    status: str

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        if v not in CAMPAIGN_STATUSES:
            raise ValueError(f"status phải thuộc {sorted(CAMPAIGN_STATUSES)}")
        return v


class CampaignAssetCreate(BaseModel):
    asset_type: str
    title: str
    content: str
    meta_data: Optional[Dict[str, Any]] = None


class ExperimentCreate(BaseModel):
    campaign_id: Optional[int] = None
    assumption_id: Optional[int] = None
    project_id: Optional[int] = None
    hypothesis: str
    method: str = "ab_test"
    metric: str
    success_threshold: Optional[str] = None
    minimum_sample: Optional[int] = 0
    timebox_days: Optional[int] = 7
    requires_external_action: bool = False
    baseline_value: float = 0.0
    target_value: float = 0.0
    variant_a: str = ""
    variant_b: str = ""
    sample_size: int = 0


class ExperimentEvaluateRequest(BaseModel):
    baseline_cvr: float
    variant_cvr: float
    baseline_sample: int
    variant_sample: int
    confidence_threshold: float = 0.95


class ExperimentDecisionRequest(BaseModel):
    decision: str
    learning: Optional[str] = None

    @field_validator("decision")
    @classmethod
    def validate_decision(cls, v: str) -> str:
        upper = v.upper()
        if upper not in EXPERIMENT_DECISIONS:
            raise ValueError(f"decision phải thuộc {sorted(EXPERIMENT_DECISIONS)}")
        return upper


class LearningCreate(BaseModel):
    observation: str
    hypothesis: str
    action: str
    result: str
    learning: str
    confidence: str = "medium"
    category: Optional[str] = None
    impact_score: Optional[float] = None
    reusable_rule: Optional[str] = None
    experiment_id: Optional[int] = None
    campaign_id: Optional[int] = None


class MetricUpsert(BaseModel):
    metric_name: str
    value: float
    category: str = "acquisition"
    unit: str = "number"
    period: Optional[str] = None
    campaign_id: Optional[int] = None

    @field_validator("category")
    @classmethod
    def validate_category(cls, v: str) -> str:
        if v not in METRIC_CATEGORIES:
            raise ValueError(f"category phải thuộc {sorted(METRIC_CATEGORIES)}")
        return v


class SkillExecuteRequest(BaseModel):
    capability_id: str
    task_input: Dict[str, Any]
    requested_by_agent: str = "Marketing Director"


class ApprovalReviewRequest(BaseModel):
    approved: bool
    review_notes: Optional[str] = None
