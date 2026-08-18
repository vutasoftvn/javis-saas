from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict

from app.business.marketing.models_validation import (
    EpistemicStatus,
    KnowledgeOrigin,
    ConfidenceLevel,
    AssumptionCategory,
    AssumptionStatus,
    EvidenceSourceType,
    EvidenceStrength,
)


class KnowledgeStatementCreate(BaseModel):
    statement: str = Field(..., min_length=1, description="Nội dung phát biểu tri thức")
    epistemic_status: EpistemicStatus = Field(default=EpistemicStatus.ASSUMPTION)
    origin: KnowledgeOrigin = Field(default=KnowledgeOrigin.AI_GENERATED)
    confidence: ConfidenceLevel = Field(default=ConfidenceLevel.LOW)
    evidence_ids: List[str] = Field(default_factory=list)
    project_id: Optional[int] = None
    meta_data: Optional[Dict[str, Any]] = None


class KnowledgeStatementResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    workspace_id: int
    brain_id: int
    project_id: Optional[int] = None
    statement: str
    epistemic_status: str
    origin: str
    confidence: str
    evidence_ids: List[str] = Field(default_factory=list)
    meta_data: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime


class AssumptionCreate(BaseModel):
    statement: str = Field(..., min_length=1, description="Giả định kinh doanh cần kiểm chứng")
    category: AssumptionCategory = Field(default=AssumptionCategory.CUSTOMER)
    project_id: Optional[int] = None
    canvas_id: Optional[str] = None
    impact: int = Field(default=3, ge=1, le=5, description="Mức độ tác động 1-5")
    uncertainty: int = Field(default=3, ge=1, le=5, description="Mức độ không chắc chắn 1-5")
    confidence: ConfidenceLevel = Field(default=ConfidenceLevel.LOW)
    status: AssumptionStatus = Field(default=AssumptionStatus.UNTESTED)
    rationale: Optional[str] = None
    evidence_ids: List[str] = Field(default_factory=list)
    experiment_ids: List[str] = Field(default_factory=list)


class AssumptionUpdate(BaseModel):
    statement: Optional[str] = None
    category: Optional[AssumptionCategory] = None
    impact: Optional[int] = Field(None, ge=1, le=5)
    uncertainty: Optional[int] = Field(None, ge=1, le=5)
    confidence: Optional[ConfidenceLevel] = None
    status: Optional[AssumptionStatus] = None
    rationale: Optional[str] = None
    evidence_ids: Optional[List[str]] = None
    experiment_ids: Optional[List[str]] = None


class AssumptionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    workspace_id: int
    brain_id: int
    project_id: Optional[int] = None
    canvas_id: Optional[str] = None
    category: str
    statement: str
    impact: int
    uncertainty: int
    criticality: int
    confidence: str
    status: str
    evidence_ids: List[str] = Field(default_factory=list)
    experiment_ids: List[str] = Field(default_factory=list)
    rationale: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class EvidenceCreate(BaseModel):
    statement: str = Field(..., min_length=1, description="Dữ liệu/bằng chứng thu thập được")
    source_type: EvidenceSourceType = Field(default=EvidenceSourceType.FOUNDER_OBSERVATION)
    source_id: Optional[str] = None
    project_id: Optional[int] = None
    supports_assumption_ids: List[str] = Field(default_factory=list)
    contradicts_assumption_ids: List[str] = Field(default_factory=list)
    strength: EvidenceStrength = Field(default=EvidenceStrength.MEDIUM)
    meta_data: Optional[Dict[str, Any]] = None
    collected_at: Optional[datetime] = None


class EvidenceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    workspace_id: int
    brain_id: int
    project_id: Optional[int] = None
    source_type: str
    source_id: Optional[str] = None
    statement: str
    supports_assumption_ids: List[str] = Field(default_factory=list)
    contradicts_assumption_ids: List[str] = Field(default_factory=list)
    strength: str
    meta_data: Optional[Dict[str, Any]] = None
    collected_at: datetime
    created_at: datetime


class AssumptionsSummaryResponse(BaseModel):
    total_assumptions: int
    untested_count: int
    testing_count: int
    supported_count: int
    partially_supported_count: int
    contradicted_count: int
    critical_untested_count: int  # criticality >= 15 & untested
    highest_criticality: int
    top_critical_assumptions: List[AssumptionResponse]


class AIExtractAssumptionsRequest(BaseModel):
    text: Optional[str] = Field(None, description="Văn bản tự do, hội thoại founder hoặc brief cần phân tích")
    canvas_type: Optional[str] = Field(None, description="Loại canvas: customer_research, product_marketing, offer_architecture")
    canvas_data: Optional[Dict[str, Any]] = Field(None, description="Dữ liệu JSON của canvas")
    project_id: Optional[int] = None
    save_to_db: bool = Field(default=False, description="Nếu true, tự động lưu assumptions vào database")


class ExtractedAssumptionItem(BaseModel):
    statement: str
    category: str
    impact: int
    uncertainty: int
    criticality: int
    confidence: str
    status: str
    rationale: Optional[str] = None
    project_id: Optional[int] = None
    canvas_id: Optional[str] = None
    should_test: bool = True


class AIExtractAssumptionsResponse(BaseModel):
    system_prompt: str
    knowledge_statements: List[Dict[str, Any]] = Field(default_factory=list)
    assumptions: List[ExtractedAssumptionItem] = Field(default_factory=list)
    total_extracted: int
    saved_count: int = 0


class CanvasDetailStatus(BaseModel):
    name: str
    status: str  # draft, hypothesis, testing, evidence_backed, contradicted, configured
    badge_label: str
    color: str
    assumptions_count: int
    untested_count: int
    testing_count: int
    evidence_backed_count: int
    contradicted_count: int


class ProjectCanvasesStatusResponse(BaseModel):
    workspace_id: int
    brain_id: int
    project_id: Optional[int] = None
    canvases: Dict[str, CanvasDetailStatus]


class AIDesignExperimentRequest(BaseModel):
    assumption_id: Optional[int] = None
    assumption_statement: Optional[str] = None
    category: Optional[str] = "customer"
    impact: Optional[int] = 4
    uncertainty: Optional[int] = 4
    project_id: Optional[int] = None


class AIDesignExperimentResponse(BaseModel):
    system_prompt: str
    assumption_statement: str
    category: str
    hypothesis: str
    method: str
    metric: str
    success_threshold: str
    minimum_sample: int
    timebox_days: int
    cost_estimate: float
    requires_external_action: bool
    required_assets: List[str] = Field(default_factory=list)
    risks: str


class ScaleWarningCheckRequest(BaseModel):
    assumption_id: int


class ScaleWarningCheckResponse(BaseModel):
    allow_scale: bool = True
    has_warning: bool = False
    warning_title: Optional[str] = None
    warning_message: Optional[str] = None
    recommendation: str = "CAMPAIGN"
    recommended_action: Optional[str] = None
    options: List[str] = Field(default_factory=list)
    message: Optional[str] = None


class CompleteValidationExperimentRequest(BaseModel):
    conclusion: str = Field(..., description="supported, partially_supported, contradicted, inconclusive")
    observations: Dict[str, Any] = Field(default_factory=dict, description="Dữ liệu quan sát thực tế")
    learning_summary: str = Field(..., min_length=1, description="Tóm tắt điều học được từ thử nghiệm")


class CompleteValidationExperimentResponse(BaseModel):
    experiment_id: str
    status: str
    conclusion: str
    learning: str
    evidence_id: Optional[str] = None
    assumption_id: Optional[str] = None
    assumption_status: Optional[str] = None
    assumption_confidence: Optional[str] = None


class CustomerInterviewCreate(BaseModel):
    contact_id: Optional[int] = None
    project_id: Optional[int] = None
    customer_name: Optional[str] = None
    segment: str = Field(default="ICP Target")
    pains: List[str] = Field(default_factory=list)
    alternatives: List[str] = Field(default_factory=list)
    objections: List[str] = Field(default_factory=list)
    willingness_to_pay: Optional[str] = None
    notable_quotes: List[str] = Field(default_factory=list)
    notes: Optional[str] = None


class CustomerInterviewResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    workspace_id: int
    brain_id: int
    project_id: Optional[int] = None
    contact_id: Optional[int] = None
    customer_name: Optional[str] = None
    segment: str
    interview_date: datetime
    pains: List[str] = Field(default_factory=list)
    alternatives: List[str] = Field(default_factory=list)
    objections: List[str] = Field(default_factory=list)
    willingness_to_pay: Optional[str] = None
    notable_quotes: List[str] = Field(default_factory=list)
    evidence_ids: List[str] = Field(default_factory=list)
    notes: Optional[str] = None
    created_at: datetime


class AIExtractInterviewRequest(BaseModel):
    transcript: str = Field(..., min_length=1, description="Nội dung ghi chú cuộc gọi hoặc transcript phỏng vấn")
    customer_name: Optional[str] = None
    segment: Optional[str] = "ICP Target"
    project_id: Optional[int] = None
    contact_id: Optional[int] = None
    save_to_db: bool = Field(default=False, description="Nếu true, tự động lưu interview và sinh evidence vào database")


class AIExtractInterviewResponse(BaseModel):
    customer_name: str
    segment: str
    interview_date: str
    pains: List[str] = Field(default_factory=list)
    alternatives: List[str] = Field(default_factory=list)
    objections: List[str] = Field(default_factory=list)
    willingness_to_pay: Optional[str] = None
    notable_quotes: List[str] = Field(default_factory=list)
    saved_interview_id: Optional[str] = None
    generated_evidence_count: int = 0


class MarketingAttributionCreate(BaseModel):
    contact_id: Optional[int] = None
    lead_id: Optional[int] = None
    campaign_id: Optional[int] = None
    experiment_id: Optional[int] = None
    variant_id: Optional[str] = None
    utm_source: Optional[str] = None
    utm_medium: Optional[str] = None
    utm_campaign: Optional[str] = None
    utm_content: Optional[str] = None
    utm_term: Optional[str] = None


class MarketingAttributionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    workspace_id: int
    contact_id: Optional[int] = None
    lead_id: Optional[int] = None
    campaign_id: Optional[int] = None
    experiment_id: Optional[int] = None
    variant_id: Optional[str] = None
    utm_source: Optional[str] = None
    utm_medium: Optional[str] = None
    utm_campaign: Optional[str] = None
    utm_content: Optional[str] = None
    utm_term: Optional[str] = None
    created_at: datetime


class AIEvaluateLearningLoopRequest(BaseModel):
    experiment_id: Optional[int] = None
    assumption_id: Optional[int] = None
    observations: Dict[str, Any] = Field(default_factory=dict)
    actual_outcome: str = Field(..., min_length=1, description="Kết quả thực tế đo lường được")


class AIEvaluateLearningLoopResponse(BaseModel):
    q1_what_happened: str
    q2_why: str
    q3_what_we_learned: str
    q4_assumption_changed: str
    q5_what_should_we_do_next: str
    decision_recommendation: str
    proposed_decision: Dict[str, Any]


class CreateLearningAndDecisionRequest(BaseModel):
    project_id: Optional[int] = None
    experiment_id: Optional[int] = None
    campaign_id: Optional[int] = None
    summary: str
    observation: Optional[str] = ""
    hypothesis: Optional[str] = ""
    action: Optional[str] = ""
    result: Optional[str] = ""
    learning: str
    affected_assumption_ids: List[str] = Field(default_factory=list)
    evidence_ids: List[str] = Field(default_factory=list)
    decision_recommendation: str = Field(default="continue", description="continue, adjust, retest, scale, stop")
    create_decision_log: bool = True
    decision_question: Optional[str] = None
    decision_text: Optional[str] = None
    decision_reason: Optional[str] = None
    next_action: Optional[str] = None
    owner: str = "Founder"


class CreateLearningAndDecisionResponse(BaseModel):
    learning_id: str
    summary: str
    decision_recommendation: str
    decision_log_id: Optional[str] = None
    decision_title: Optional[str] = None
    decision_text: Optional[str] = None


class DecisionLogItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    workspace_id: int
    brain_id: int
    project_id: Optional[int] = None
    campaign_id: Optional[int] = None
    experiment_id: Optional[int] = None
    title: str
    question: Optional[str] = None
    decision: str
    reason: str
    based_on_assumption_ids: List[str] = Field(default_factory=list)
    based_on_evidence_ids: List[str] = Field(default_factory=list)
    next_action: Optional[str] = None
    owner: Optional[str] = None
    created_at: datetime


class AIProposeCanvasRevisionRequest(BaseModel):
    canvas_type: str = Field(..., description="customer_research, product_marketing, offer, brand")
    current_canvas: Dict[str, Any]
    evidence_statement: str
    is_contradiction: bool = False
    affected_field: Optional[str] = None


class AIProposeCanvasRevisionResponse(BaseModel):
    canvas_type: str
    changed_fields: List[str] = Field(default_factory=list)
    previous_snapshot: Dict[str, Any]
    new_snapshot: Dict[str, Any]
    reason: str
    is_contradiction: bool


class CanvasRevisionCreateProposalRequest(BaseModel):
    project_id: Optional[int] = None
    canvas_type: str
    changed_fields: List[str] = Field(default_factory=list)
    previous_snapshot: Dict[str, Any]
    new_snapshot: Dict[str, Any]
    reason: str
    evidence_ids: List[str] = Field(default_factory=list)
    auto_approve: bool = False


class CanvasRevisionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    workspace_id: int
    brain_id: int
    project_id: Optional[int] = None
    canvas_type: str
    status: str
    changed_fields: List[str] = Field(default_factory=list)
    previous_snapshot: Optional[Dict[str, Any]] = None
    new_snapshot: Optional[Dict[str, Any]] = None
    reason: str
    evidence_ids: List[str] = Field(default_factory=list)
    approved_by: Optional[int] = None
    created_at: datetime





