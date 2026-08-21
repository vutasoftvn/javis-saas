from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

from app.founder_os.validation.models import (
    ValidationWorkflowState,
    EpistemicType,
    ClaimConfirmationStatus,
    DimensionName,
    DimensionStateEnum,
    FeasibilityPillar,
    AssumptionCategory,
    AssumptionStatus,
    ExperimentType,
    EvidenceType,
    EvidenceRelationship,
    ReviewProviderType,
    ReviewVerdict,
    FounderDecisionEnum,
)


# -------------------------------------------------------------------------
# SESSION & WORKFLOW SCHEMAS
# -------------------------------------------------------------------------

class ValidationSessionStartRequest(BaseModel):
    initial_topic: Optional[DimensionName] = DimensionName.CUSTOMER
    interview_mode: bool = True


class ValidationSessionResponse(BaseModel):
    id: int
    workspace_id: int
    brain_id: int
    project_id: int
    current_topic: str
    workflow_state: str
    interview_mode_active: bool
    fields_status_jsonb: Dict[str, Any] = {}
    created_at: datetime
    updated_at: datetime


class ValidationChatRequest(BaseModel):
    message: str
    current_topic: Optional[str] = None


class ValidationChatResponse(BaseModel):
    session_id: int
    current_topic: str
    ai_reply: str
    extracted_claims: List[Dict[str, Any]] = []
    is_topic_cluster_complete: bool = False
    cluster_summary: Optional[Dict[str, Any]] = None
    next_questions: List[str] = []
    suggested_next_topic: Optional[str] = None
    question_graph_suggestion: Optional[str] = None


class QuestionGraphNodeResponse(BaseModel):
    id: str
    stage: str
    dimension: str
    question_type: str
    prompt_vi: str
    purpose: str


class QuestionGraphSuggestionResponse(BaseModel):
    project_id: int
    node: Optional[QuestionGraphNodeResponse] = None
    rationale: str
    answered_count: int
    total: int


# -------------------------------------------------------------------------
# STRUCTURED CLAIMS & REVISIONS SCHEMAS
# -------------------------------------------------------------------------

class StructuredClaimCreate(BaseModel):
    dimension: DimensionName
    subject: str
    predicate: str
    value: Any
    epistemic_type: Optional[EpistemicType] = EpistemicType.ASSUMPTION
    source_type: Optional[str] = "FOUNDER_CHAT"
    source_actor: Optional[str] = "FOUNDER"
    source_ref: Optional[str] = None
    confidence: Optional[float] = 1.0


class StructuredClaimConfirmRequest(BaseModel):
    confidence: Optional[float] = 1.0


class StructuredClaimEditRequest(BaseModel):
    new_value: Any
    reason: Optional[str] = "Founder edit"


class FieldRevisionResponse(BaseModel):
    id: int
    project_id: int
    claim_id: Optional[int] = None
    field_path: str
    old_value_jsonb: Optional[Dict[str, Any]] = None
    new_value_jsonb: Dict[str, Any]
    changed_by: str
    reason: Optional[str] = None
    created_at: datetime


class StructuredClaimResponse(BaseModel):
    id: int
    workspace_id: int
    project_id: int
    session_id: Optional[int] = None
    dimension: str
    subject: str
    predicate: str
    value_jsonb: Dict[str, Any]
    epistemic_type: str
    confirmation_status: str
    source_type: str
    source_actor: str
    source_ref: Optional[str] = None
    confidence: float
    supersedes_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime


# -------------------------------------------------------------------------
# ASSUMPTION SCHEMAS
# -------------------------------------------------------------------------

class AssumptionCreate(BaseModel):
    category: AssumptionCategory = AssumptionCategory.CUSTOMER
    statement: str
    importance: int = Field(default=3, ge=1, le=5)
    uncertainty: int = Field(default=3, ge=1, le=5)
    impact: int = Field(default=3, ge=1, le=5)
    source: Optional[str] = "FOUNDER_CHAT"
    claim_id: Optional[int] = None
    owner: Optional[str] = None


class AssumptionUpdate(BaseModel):
    statement: Optional[str] = None
    importance: Optional[int] = Field(default=None, ge=1, le=5)
    uncertainty: Optional[int] = Field(default=None, ge=1, le=5)
    impact: Optional[int] = Field(default=None, ge=1, le=5)
    status: Optional[AssumptionStatus] = None
    confidence: Optional[float] = None
    owner: Optional[str] = None


class AssumptionResponse(BaseModel):
    id: int
    workspace_id: int
    project_id: int
    claim_id: Optional[int] = None
    category: str
    statement: str
    importance: int
    uncertainty: int
    impact: int
    risk_score: int
    source: str
    status: str
    confidence: float
    owner: Optional[str] = None
    created_at: datetime
    updated_at: datetime


# -------------------------------------------------------------------------
# HYPOTHESIS SCHEMAS
# -------------------------------------------------------------------------

class HypothesisCreate(BaseModel):
    assumption_id: int
    action: str
    target_segment: str
    metric: str
    threshold: str
    timeframe_days: int = Field(default=7, ge=1)


class HypothesisResponse(BaseModel):
    id: int
    workspace_id: int
    project_id: int
    assumption_id: int
    action: str
    target_segment: str
    metric: str
    threshold: str
    timeframe_days: int
    statement: str
    quality_gate_passed: bool
    status: str
    created_at: datetime
    updated_at: datetime


# -------------------------------------------------------------------------
# EXPERIMENT SCHEMAS
# -------------------------------------------------------------------------

class ExperimentCreate(BaseModel):
    hypothesis_id: int
    experiment_type: ExperimentType = ExperimentType.CUSTOMER_INTERVIEW
    name: str
    description: Optional[str] = None
    smallest_useful_scope: Optional[str] = None
    success_threshold: str
    budget_amount: float = 0.0
    duration_days: int = 7


class ExperimentResponse(BaseModel):
    id: int
    workspace_id: int
    project_id: int
    hypothesis_id: int
    experiment_type: str
    name: str
    description: Optional[str] = None
    smallest_useful_scope: Optional[str] = None
    success_threshold: str
    budget_amount: float
    duration_days: int
    status: str
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    results_summary: Optional[str] = None
    created_at: datetime
    updated_at: datetime


# -------------------------------------------------------------------------
# EVIDENCE SCHEMAS
# -------------------------------------------------------------------------

class EvidenceCreate(BaseModel):
    assumption_id: Optional[int] = None
    hypothesis_id: Optional[int] = None
    experiment_id: Optional[int] = None
    evidence_type: EvidenceType = EvidenceType.CUSTOMER_INTERVIEW
    source_type: str
    source_ref: Optional[str] = None
    observation: str
    metric_name: Optional[str] = None
    metric_value: Optional[str] = None
    relationship: EvidenceRelationship = EvidenceRelationship.SUPPORTS
    confidence: float = 0.8
    attachments: Optional[List[Dict[str, Any]]] = None


class EvidenceResponse(BaseModel):
    id: int
    workspace_id: int
    project_id: int
    assumption_id: Optional[int] = None
    hypothesis_id: Optional[int] = None
    experiment_id: Optional[int] = None
    evidence_type: str
    source_type: str
    source_ref: Optional[str] = None
    observation: str
    metric_name: Optional[str] = None
    metric_value: Optional[str] = None
    relationship: str
    confidence: float
    attachments_jsonb: List[Any] = []
    captured_at: datetime
    created_at: datetime


# -------------------------------------------------------------------------
# REVIEW & DECISION SCHEMAS
# -------------------------------------------------------------------------

class ValidationReviewCreate(BaseModel):
    hypothesis_id: Optional[int] = None
    review_provider_type: ReviewProviderType = ReviewProviderType.AI
    verdict: ReviewVerdict = ReviewVerdict.TEST_MORE
    confidence_score: float = 0.7
    supported_points: List[str] = []
    challenged_points: List[str] = []
    missing_evidence: List[str] = []
    critical_risks: List[str] = []
    recommended_next_action: Optional[str] = None
    human_review_recommended: bool = False
    raw_report: Optional[str] = None


class ValidationReviewResponse(BaseModel):
    id: int
    workspace_id: int
    project_id: int
    hypothesis_id: Optional[int] = None
    review_provider_type: str
    verdict: str
    confidence_score: float
    supported_points: List[Any] = []
    challenged_points: List[Any] = []
    missing_evidence: List[Any] = []
    critical_risks: List[Any] = []
    recommended_next_action: Optional[str] = None
    human_review_recommended: bool
    raw_report: Optional[str] = None
    created_at: datetime


class ValidationDecisionCreate(BaseModel):
    review_id: Optional[int] = None
    founder_decision: FounderDecisionEnum = FounderDecisionEnum.PROCEED
    rationale: Optional[str] = None
    risks_acknowledged: List[str] = []


class ValidationDecisionResponse(BaseModel):
    id: int
    workspace_id: int
    project_id: int
    review_id: Optional[int] = None
    ai_recommendation: Optional[str] = None
    founder_decision: str
    rationale: Optional[str] = None
    risks_acknowledged: List[Any] = []
    decided_at: datetime
    created_at: datetime


# -------------------------------------------------------------------------
# STATE VECTOR & COMPOSITE SCHEMAS
# -------------------------------------------------------------------------

class DimensionStateResponse(BaseModel):
    dimension: str
    pillar: str
    state: str
    confidence: float
    summary: Optional[str] = None
    updated_at: datetime


class StateVectorResponse(BaseModel):
    project_id: int
    project_stage: str
    workflow_state: str
    overall_confidence: float
    dimensions: Dict[str, DimensionStateResponse]
    critical_assumptions_count: int
    active_experiments_count: int
    primary_next_best_action: Optional[str] = None


# -------------------------------------------------------------------------
# PHASE 3: RISK MATRIX & EXPERIMENT SCHEMAS
# -------------------------------------------------------------------------

class RiskQuadrantItem(BaseModel):
    id: int
    category: str
    statement: str
    importance: int
    uncertainty: int
    risk_score: int
    status: str
    confidence: float


class RiskMatrixResponse(BaseModel):
    project_id: int
    critical_risks: List[RiskQuadrantItem] = []      # Importance >= 4, Uncertainty >= 4 (Risk 16-25)
    monitor_risks: List[RiskQuadrantItem] = []       # Importance >= 4, Uncertainty <= 3 (Risk 4-15)
    exploratory_risks: List[RiskQuadrantItem] = []   # Importance <= 3, Uncertainty >= 4 (Risk 4-15)
    low_risks: List[RiskQuadrantItem] = []           # Importance <= 3, Uncertainty <= 3 (Risk 1-9)
    total_assumptions: int
    highest_risk_score: int


class GeneratedHypothesisResponse(BaseModel):
    assumption_id: int
    action: str
    target_segment: str
    metric: str
    threshold: str
    timeframe_days: int
    statement: str
    rationale: Optional[str] = None


class RecommendedExperimentResponse(BaseModel):
    hypothesis_id: int
    experiment_type: str
    name: str
    description: str
    smallest_useful_scope: str
    success_threshold: str
    duration_days: int
    budget_amount: float


class NextBestActionDetailResponse(BaseModel):
    project_id: int
    title: str
    why: str
    risk_category: str
    risk_score: int
    recommended_experiment: Optional[str] = None
    target_threshold: Optional[str] = None
    timeframe_days: int = 7
    priority: str = "P0_CRITICAL"


class ReviewPackageResponse(BaseModel):
    project_id: int
    project_stage: str
    hypothesis_id: int
    hypothesis_statement: str
    claims_count: int
    assumptions_count: int
    evidence_count: int
    exported_at: datetime
    read_only_bundle: Dict[str, Any]
    human_review_enabled: bool = False


# -------------------------------------------------------------------------
# F2 / F3: CUSTOMER DISCOVERY, AUDIT & SCORECARD SCHEMAS
# -------------------------------------------------------------------------

class QuestionAuditRequest(BaseModel):
    question: str
    research_objective: Optional[str] = None


class QuestionAuditResponse(BaseModel):
    original_question: str
    classification: str  # PAST_BEHAVIOR, LEADING, OPINION, etc.
    is_biased_or_leading: bool
    warning_message: Optional[str] = None
    suggested_rewrites: List[str] = []
    reasoning: Optional[str] = None


class InterviewScriptGenerateRequest(BaseModel):
    target_segment: Optional[str] = None
    focus_topic: Optional[str] = None


class InterviewScriptResponse(BaseModel):
    script_title: str
    target_segment: str
    steps: List[Dict[str, Any]]
    counter_bias_tips: List[str] = []


class CustomerContactCreate(BaseModel):
    name: str
    role: str = "USER"
    segment: Optional[str] = None
    company: Optional[str] = None
    contact_info: Optional[str] = None
    notes: Optional[str] = None


class CustomerContactResponse(BaseModel):
    id: int
    project_id: int
    name: str
    role: str
    segment: Optional[str] = None
    company: Optional[str] = None
    contact_info: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime


class InterviewSessionCreate(BaseModel):
    contact_id: Optional[int] = None
    role: str = "USER"
    segment: Optional[str] = None
    interview_date: Optional[datetime] = None
    duration_minutes: int = 30
    raw_notes: Optional[str] = None
    transcript: Optional[str] = None
    session_summary: Optional[str] = None
    referral_notes: Optional[str] = None


class InterviewSessionResponse(BaseModel):
    id: int
    project_id: int
    contact_id: Optional[int] = None
    role: str
    segment: Optional[str] = None
    interview_date: datetime
    duration_minutes: int
    raw_notes: Optional[str] = None
    transcript: Optional[str] = None
    session_summary: Optional[str] = None
    referral_notes: Optional[str] = None
    quotes_count: int = 0
    created_at: datetime


class VerbatimQuoteCreate(BaseModel):
    raw_quote: str
    interpretation: Optional[str] = None
    interpretation_actor: str = "AI"
    tags: List[str] = []
    buying_signal_level: Optional[str] = None
    linked_assumption_id: Optional[int] = None


class VerbatimQuoteResponse(BaseModel):
    id: int
    project_id: int
    session_id: int
    raw_quote: str
    interpretation: Optional[str] = None
    interpretation_actor: str
    tags: List[str] = []
    buying_signal_level: Optional[str] = None
    linked_assumption_id: Optional[int] = None
    created_at: datetime


class ProblemScorecardRequest(BaseModel):
    frequency_score: int = Field(ge=1, le=10)
    severity_score: int = Field(ge=1, le=10)
    alternatives_score: int = Field(ge=1, le=10)
    wtp_score: int = Field(ge=1, le=10)
    market_potential_score: int = Field(ge=1, le=10)
    notes: Optional[str] = None


class ProblemScorecardResponse(BaseModel):
    id: Optional[int] = None
    project_id: int
    frequency_score: int
    severity_score: int
    alternatives_score: int
    wtp_score: int
    market_potential_score: int
    total_score: int
    framework_threshold: int = 40
    interpretation_result: str
    evidence_quality: str
    evidence_refs: List[Any] = []
    notes: Optional[str] = None
    updated_at: Optional[datetime] = None


class DataAutopsyResponse(BaseModel):
    project_id: int
    total_interviews: int
    total_quotes: int
    patterns: List[Dict[str, Any]] = []
    niches: List[Dict[str, Any]] = []
    shocks: List[Dict[str, Any]] = []
    recommended_problem_statement: Optional[str] = None
    recommended_jtbd: Optional[Dict[str, str]] = None


class RoleCoverageResponse(BaseModel):
    project_id: int
    user_count: int
    buyer_count: int
    decision_maker_count: int
    influencer_count: int
    total_interviews: int
    has_decision_maker_gap: bool
    warning_message: Optional[str] = None
    coverage_status: Dict[str, bool]


class SolutionBiasRiskResponse(BaseModel):
    project_id: int
    solution_bias_risk: str  # NONE, LOW, MEDIUM, HIGH
    solution_maturity: str
    problem_evidence_maturity: str
    warning_title: Optional[str] = None
    warning_message: Optional[str] = None
    recommended_action: str
    counter_questions: List[str] = []
    allow_proceed_anyway: bool = True




