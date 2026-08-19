from datetime import datetime
from typing import Optional, List, Any, Dict
from pydantic import BaseModel, Field, ConfigDict



class SourceDocumentBase(BaseModel):
    title: str
    authority: Optional[str] = None
    document_type: str = "PROGRAM_GUIDE"
    document_number: Optional[str] = None
    issued_at: Optional[datetime] = None
    source_url: Optional[str] = None
    verification_status: str = "UNVERIFIED"
    verification_note: Optional[str] = None


class SourceDocumentCreate(SourceDocumentBase):
    pass


class SourceDocumentResponse(SourceDocumentBase):
    id: int
    id_str: str
    workspace_id: int
    brain_id: int
    file_hash: Optional[str] = None
    verified_by: Optional[int] = None
    verified_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PolicyProgramClaimBase(BaseModel):
    claim_type: str = "SUPPORT_AMOUNT"
    claim_key: str
    claim_value: str
    source_page: Optional[int] = None
    source_excerpt: Optional[str] = None
    is_verified: bool = False
    verified_value: Optional[str] = None


class PolicyProgramClaimCreate(PolicyProgramClaimBase):
    program_id: int
    source_document_id: Optional[int] = None


class PolicyProgramClaimUpdate(BaseModel):
    claim_value: Optional[str] = None
    is_verified: Optional[bool] = None
    verified_value: Optional[str] = None


class PolicyProgramClaimResponse(PolicyProgramClaimBase):
    id: int
    id_str: str
    program_id: int
    source_document_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PolicyVerificationCreate(BaseModel):
    result_status: str = "VERIFIED_ACTIVE"  # VERIFIED_ACTIVE, VERIFIED_ENACTED, VERIFIED_CLOSED, REJECTED_SOURCE_DATA, PENDING_FOUNDER_VERIFICATION
    official_source_url: Optional[str] = None
    official_authority: Optional[str] = None
    official_document_id: Optional[int] = None
    notes: Optional[str] = None
    diff_jsonb: Dict[str, Any] = Field(default_factory=dict)
    updated_claims: Dict[str, str] = Field(default_factory=dict)  # claim_id -> verified_value


class PolicyVerificationResponse(BaseModel):
    id: int
    id_str: str
    program_id: int
    verified_by: Optional[int] = None
    verified_at: datetime
    official_source_url: Optional[str] = None
    official_authority: Optional[str] = None
    result_status: str
    notes: Optional[str] = None
    diff_jsonb: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PolicyChangeProposalCreate(BaseModel):
    program_id: Optional[int] = None
    change_type: str
    field_name: Optional[str] = None
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    source_url: Optional[str] = None
    source_excerpt: Optional[str] = None
    confidence: float = 0.0
    ai_model: Optional[str] = None


class PolicyChangeProposalReview(BaseModel):
    review_status: str = "APPROVED"  # APPROVED, REJECTED
    review_notes: Optional[str] = None


class PolicyChangeProposalResponse(BaseModel):
    id: int
    id_str: str
    program_id: Optional[int] = None
    change_type: str
    field_name: Optional[str] = None
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    source_url: Optional[str] = None
    source_excerpt: Optional[str] = None
    confidence: float
    ai_model: Optional[str] = None
    review_status: str
    reviewed_by: Optional[int] = None
    reviewed_at: Optional[datetime] = None
    review_notes: Optional[str] = None
    detected_at: datetime
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PolicyProgramBase(BaseModel):
    name: str
    code: Optional[str] = None
    summary: Optional[str] = None
    program_type: str = "GRANT"
    legal_basis: Optional[str] = None
    authority: Optional[str] = None
    geography: Optional[str] = "NATIONAL"
    company_types: List[str] = Field(default_factory=list)
    project_stages: List[str] = Field(default_factory=list)
    trl_min: Optional[int] = None
    industries: List[str] = Field(default_factory=list)
    funding_min: Optional[float] = None
    funding_max: Optional[float] = None
    currency: str = "VND"
    matching_fund_pct: Optional[float] = 0.0
    eligible_costs: List[str] = Field(default_factory=list)
    status: str = "DRAFT"
    verification_status: str = "PENDING_FOUNDER_VERIFICATION"
    matching_mode: str = "soft"
    publish_to_matching: bool = True
    source_claim: Optional[str] = None
    claimed_values_jsonb: Dict[str, Any] = Field(default_factory=dict)
    source_url: Optional[str] = None
    application_window_start: Optional[datetime] = None
    application_window_end: Optional[datetime] = None


class PolicyProgramCreate(PolicyProgramBase):
    source_document_id: Optional[int] = None


class PolicyProgramUpdate(BaseModel):
    name: Optional[str] = None
    summary: Optional[str] = None
    status: Optional[str] = None
    verification_status: Optional[str] = None
    matching_mode: Optional[str] = None
    publish_to_matching: Optional[bool] = None
    source_claim: Optional[str] = None
    funding_min: Optional[float] = None
    funding_max: Optional[float] = None
    matching_fund_pct: Optional[float] = None
    application_window_start: Optional[datetime] = None
    application_window_end: Optional[datetime] = None


class PolicyProgramResponse(PolicyProgramBase):
    id: int
    id_str: str
    workspace_id: int
    brain_id: int
    source_document_id: Optional[int] = None
    last_verified_at: Optional[datetime] = None
    claims: List[PolicyProgramClaimResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class EligibilityRuleBase(BaseModel):
    rule_type: str = "HARD"
    category: str = "LEGAL"
    title: str
    description: Optional[str] = None
    field_path: Optional[str] = None
    operator: Optional[str] = None
    expected_value_jsonb: Dict[str, Any] = Field(default_factory=dict)
    legal_reference: Optional[str] = None
    weight: float = 1.0


class EligibilityRuleCreate(EligibilityRuleBase):
    program_id: int
    source_document_id: Optional[int] = None


class EligibilityRuleResponse(EligibilityRuleBase):
    id: int
    id_str: str
    program_id: int
    source_document_id: Optional[int] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ProjectStageAssessmentCreate(BaseModel):
    company_type: str = "STARTUP"
    stage: str = "MVP"
    is_founder_confirmed: bool = True
    notes: Optional[str] = None


class ProjectStageAssessmentResponse(BaseModel):
    id: int
    id_str: str
    project_id: int
    company_type: str
    stage: str
    ai_suggested_type: Optional[str] = None
    ai_suggested_stage: Optional[str] = None
    ai_confidence_score: Optional[float] = None
    is_founder_confirmed: bool
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TrlAssessmentCreate(BaseModel):
    trl_current: int = Field(ge=1, le=9)
    trl_target: Optional[int] = Field(default=None, ge=1, le=9)
    explanation: Optional[str] = None
    evidence_artifact_id: Optional[int] = None
    evidence_notes: Optional[str] = None


class TrlAssessmentResponse(BaseModel):
    id: int
    id_str: str
    project_id: int
    trl_current: int
    trl_target: Optional[int] = None
    explanation: Optional[str] = None
    evidence_artifact_id: Optional[int] = None
    evidence_notes: Optional[str] = None
    assessed_by: Optional[int] = None
    verified_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MissingRequirementResponse(BaseModel):
    id: int
    id_str: str
    project_id: int
    program_id: int
    category: str
    title: str
    description: Optional[str] = None
    is_resolved: bool
    linked_task_id: Optional[int] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ProjectProgramMatchResponse(BaseModel):
    id: int
    id_str: str
    project_id: int
    program_id: int
    program_name: Optional[str] = None
    program_status: Optional[str] = None
    program_authority: Optional[str] = None
    program_type: Optional[str] = None
    eligibility_status: str  # ELIGIBLE, POTENTIALLY_ELIGIBLE, INELIGIBLE, NEEDS_VERIFICATION
    match_score: float  # 0..100
    readiness_score: float  # 0..100
    pipeline_stage: str
    passed_rules_count: int
    total_rules_count: int
    ai_summary: Optional[str] = None
    calculated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class FundingOverviewResponse(BaseModel):
    project_id: int
    project_id_str: str
    project_title: str
    company_type: str
    project_stage: str
    trl_current: int
    readiness_score_avg: float
    top_matches: List[ProjectProgramMatchResponse]
    missing_requirements: List[MissingRequirementResponse]
    active_awards_count: int
    urgent_alerts: List[str]


class Create12wyTaskRequest(BaseModel):
    missing_requirement_id: int
    cycle_id: Optional[int] = None
    week_no: int = 1
    custom_title: Optional[str] = None


class DoubleFundingCheckRequest(BaseModel):
    project_id: int
    work_package: str
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None
    cost_category: str
    purpose: str
    amount: float


class DoubleFundingWarning(BaseModel):
    conflict_found: bool
    message: str
    conflicting_award_ids: List[int] = Field(default_factory=list)
    conflicting_application_ids: List[int] = Field(default_factory=list)


class AdminVerifyRequest(BaseModel):
    status: str = "VERIFIED"  # VERIFIED, PUBLISHED, REJECTED, DRAFT
    verification_note: Optional[str] = None
    publish_to_catalog: bool = False
