from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any, List

from sqlalchemy import String, Boolean, DateTime, ForeignKey, BigInteger, Text, Integer, Float, Index, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base
from app.core.snowflake import generate_snowflake_id


class ProjectStage(str, Enum):
    IDEA = "IDEA"
    VALIDATION = "VALIDATION"
    MVP = "MVP"
    EARLY_TRACTION = "EARLY_TRACTION"
    GROWTH = "GROWTH"
    SCALE = "SCALE"
    PAUSED = "PAUSED"
    SUNSET = "SUNSET"


class ValidationWorkflowState(str, Enum):
    UNASSESSED = "UNASSESSED"
    DATA_COLLECTION = "DATA_COLLECTION"
    ASSUMPTION_MAPPED = "ASSUMPTION_MAPPED"
    RISK_PRIORITIZED = "RISK_PRIORITIZED"
    HYPOTHESIS_READY = "HYPOTHESIS_READY"
    EXPERIMENT_READY = "EXPERIMENT_READY"
    TESTING = "TESTING"
    EVIDENCE_READY = "EVIDENCE_READY"
    REVIEW_READY = "REVIEW_READY"
    DECIDED = "DECIDED"
    PIVOT_REQUIRED = "PIVOT_REQUIRED"


class EpistemicType(str, Enum):
    FACT = "FACT"
    BELIEF = "BELIEF"
    ASSUMPTION = "ASSUMPTION"
    HYPOTHESIS = "HYPOTHESIS"
    EVIDENCE = "EVIDENCE"
    DECISION = "DECISION"


class ClaimConfirmationStatus(str, Enum):
    DRAFT = "DRAFT"
    AI_INFERRED = "AI_INFERRED"
    FOUNDER_CONFIRMED = "FOUNDER_CONFIRMED"
    FOUNDER_EDITED = "FOUNDER_EDITED"
    EVIDENCE_SUPPORTED = "EVIDENCE_SUPPORTED"
    CHALLENGED = "CHALLENGED"
    SUPERSEDED = "SUPERSEDED"


class DimensionName(str, Enum):
    FOUNDER_FIT = "FOUNDER_FIT"
    CUSTOMER = "CUSTOMER"
    PROBLEM = "PROBLEM"
    SOLUTION = "SOLUTION"
    PRICING = "PRICING"
    CHANNEL = "CHANNEL"
    REVENUE = "REVENUE"
    GROWTH = "GROWTH"
    TECHNICAL = "TECHNICAL"
    OPERATIONAL = "OPERATIONAL"
    LEGAL = "LEGAL"
    FINANCE = "FINANCE"


class DimensionStateEnum(str, Enum):
    UNKNOWN = "UNKNOWN"
    BELIEF = "BELIEF"
    ASSUMPTION = "ASSUMPTION"
    HYPOTHESIS = "HYPOTHESIS"
    TESTING = "TESTING"
    SUPPORTED = "SUPPORTED"
    CHALLENGED = "CHALLENGED"
    VALIDATED = "VALIDATED"
    INVALIDATED = "INVALIDATED"


class FeasibilityPillar(str, Enum):
    DESIRABILITY = "DESIRABILITY"
    VIABILITY = "VIABILITY"
    FEASIBILITY = "FEASIBILITY"
    FOUNDER_FIT = "FOUNDER_FIT"


class AssumptionCategory(str, Enum):
    FOUNDER = "FOUNDER"
    CUSTOMER = "CUSTOMER"
    PROBLEM = "PROBLEM"
    SOLUTION = "SOLUTION"
    PRICING = "PRICING"
    CHANNEL = "CHANNEL"
    REVENUE = "REVENUE"
    GROWTH = "GROWTH"
    TECHNICAL = "TECHNICAL"
    OPERATIONAL = "OPERATIONAL"
    LEGAL = "LEGAL"
    FINANCE = "FINANCE"


class AssumptionStatus(str, Enum):
    UNKNOWN = "UNKNOWN"
    UNTESTED = "UNTESTED"
    HYPOTHESIZED = "HYPOTHESIZED"
    TESTING = "TESTING"
    SUPPORTED = "SUPPORTED"
    CHALLENGED = "CHALLENGED"
    VALIDATED = "VALIDATED"
    INVALIDATED = "INVALIDATED"


class ExperimentType(str, Enum):
    CUSTOMER_INTERVIEW = "CUSTOMER_INTERVIEW"
    LANDING_PAGE = "LANDING_PAGE"
    FAKE_DOOR = "FAKE_DOOR"
    WAITLIST = "WAITLIST"
    PREORDER = "PREORDER"
    PAID_OFFER = "PAID_OFFER"
    CONCIERGE_MVP = "CONCIERGE_MVP"
    PROTOTYPE_TEST = "PROTOTYPE_TEST"
    A_B_TEST = "A_B_TEST"
    SALES_CALL = "SALES_CALL"
    CHANNEL_TEST = "CHANNEL_TEST"
    PRICING_TEST = "PRICING_TEST"


class EvidenceType(str, Enum):
    REAL_PAYMENT = "REAL_PAYMENT"
    DEPOSIT_PREORDER = "DEPOSIT_PREORDER"
    ACTION_COMMITMENT = "ACTION_COMMITMENT"
    OBSERVED_BEHAVIOR = "OBSERVED_BEHAVIOR"
    TIME_INVESTMENT = "TIME_INVESTMENT"
    CUSTOMER_INTERVIEW = "CUSTOMER_INTERVIEW"
    SURVEY = "SURVEY"
    SOCIAL_PRAISE = "SOCIAL_PRAISE"
    DESK_RESEARCH = "DESK_RESEARCH"
    AI_ANALYSIS = "AI_ANALYSIS"
    FOUNDER_BELIEF = "FOUNDER_BELIEF"


class QuestionTypeEnum(str, Enum):
    PAST_BEHAVIOR = "PAST_BEHAVIOR"
    CURRENT_BEHAVIOR = "CURRENT_BEHAVIOR"
    OPINION = "OPINION"
    HYPOTHETICAL_FUTURE = "HYPOTHETICAL_FUTURE"
    LEADING = "LEADING"
    SOLUTION_PITCH = "SOLUTION_PITCH"
    COST_DISCOVERY = "COST_DISCOVERY"
    ALTERNATIVE_DISCOVERY = "ALTERNATIVE_DISCOVERY"


class BuyingSignalLevelEnum(str, Enum):
    LEVEL_1_INTEREST = "LEVEL_1_INTEREST"
    LEVEL_2_PAIN = "LEVEL_2_PAIN"
    LEVEL_3_WTP = "LEVEL_3_WTP"
    LEVEL_4_ACTION = "LEVEL_4_ACTION"
    LEVEL_5_STRONG_PROOF = "LEVEL_5_STRONG_PROOF"


class CustomerRoleEnum(str, Enum):
    USER = "USER"
    BUYER = "BUYER"
    DECISION_MAKER = "DECISION_MAKER"
    INFLUENCER = "INFLUENCER"


class ICPLifecycleState(str, Enum):
    HYPOTHESIZED = "HYPOTHESIZED"
    EVIDENCE_BUILDING = "EVIDENCE_BUILDING"
    EVIDENCE_BACKED = "EVIDENCE_BACKED"
    CHALLENGED = "CHALLENGED"
    SUPERSEDED = "SUPERSEDED"


class AutopsyClusterType(str, Enum):
    PATTERN = "PATTERN"
    NICHE = "NICHE"
    SHOCK = "SHOCK"


class ProblemValidationResultEnum(str, Enum):
    PROBLEM_NOT_ESTABLISHED = "PROBLEM_NOT_ESTABLISHED"
    PROBLEM_WEAKLY_SUPPORTED = "PROBLEM_WEAKLY_SUPPORTED"
    PROBLEM_SUPPORTED = "PROBLEM_SUPPORTED"
    PROBLEM_STRONGLY_SUPPORTED = "PROBLEM_STRONGLY_SUPPORTED"


class EvidenceRelationship(str, Enum):
    SUPPORTS = "SUPPORTS"
    CHALLENGES = "CHALLENGES"
    COMPLICATES = "COMPLICATES"
    NEUTRAL = "NEUTRAL"


class ReviewProviderType(str, Enum):
    AI = "AI"
    HUMAN_INTERNAL = "HUMAN_INTERNAL"
    HUMAN_EXPERT = "HUMAN_EXPERT"
    MENTOR = "MENTOR"
    ADVISOR = "ADVISOR"
    PANEL = "PANEL"


class ReviewVerdict(str, Enum):
    PASS = "PASS"
    CONDITIONAL_PASS = "CONDITIONAL_PASS"
    TEST_MORE = "TEST_MORE"
    CHALLENGED = "CHALLENGED"
    FAIL = "FAIL"


class FounderDecisionEnum(str, Enum):
    PROCEED = "PROCEED"
    TEST_MORE = "TEST_MORE"
    PIVOT = "PIVOT"
    PAUSE = "PAUSE"
    STOP = "STOP"


# -------------------------------------------------------------------------
# DATABASE TABLES (F1.md §50 - §52)
# -------------------------------------------------------------------------

class ValidationSession(Base):
    """
    Quản lý phiên phỏng vấn / kiểm chứng dự án.
    """
    __tablename__ = "validation_sessions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    brain_id: Mapped[int] = mapped_column(ForeignKey("brains.id"), index=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), index=True)

    current_topic: Mapped[str] = mapped_column(String(50), default=DimensionName.CUSTOMER.value)
    workflow_state: Mapped[str] = mapped_column(String(50), default=ValidationWorkflowState.UNASSESSED.value, index=True)
    
    interview_mode_active: Mapped[bool] = mapped_column(Boolean, default=False)
    fields_status_jsonb: Mapped[dict] = mapped_column(JSONB, default=dict)
    session_metadata: Mapped[dict] = mapped_column(JSONB, default=dict)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class StructuredClaim(Base):
    """
    Dữ kiện có cấu trúc bóc tách từ hội thoại hoặc nguồn khác (F1.md §51).
    """
    __tablename__ = "structured_claims"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    brain_id: Mapped[int] = mapped_column(ForeignKey("brains.id"), index=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), index=True)
    session_id: Mapped[Optional[int]] = mapped_column(ForeignKey("validation_sessions.id"), nullable=True, index=True)

    dimension: Mapped[str] = mapped_column(String(50), index=True)
    subject: Mapped[str] = mapped_column(String(100), index=True)
    predicate: Mapped[str] = mapped_column(String(100), index=True)
    value_jsonb: Mapped[dict] = mapped_column(JSONB, default=dict)
    
    epistemic_type: Mapped[str] = mapped_column(String(50), default=EpistemicType.ASSUMPTION.value, index=True)
    confirmation_status: Mapped[str] = mapped_column(String(50), default=ClaimConfirmationStatus.AI_INFERRED.value, index=True)
    
    source_type: Mapped[str] = mapped_column(String(50), default="FOUNDER_CHAT")
    source_actor: Mapped[str] = mapped_column(String(50), default="FOUNDER")
    source_ref: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    confidence: Mapped[float] = mapped_column(Float, default=1.0)
    
    supersedes_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class FieldRevision(Base):
    """
    Lưu vết sửa đổi bất biến khi dữ liệu thay đổi (F1.md §52).
    """
    __tablename__ = "field_revisions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), index=True)
    claim_id: Mapped[Optional[int]] = mapped_column(ForeignKey("structured_claims.id"), nullable=True, index=True)

    field_path: Mapped[str] = mapped_column(String(255), index=True)
    old_value_jsonb: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    new_value_jsonb: Mapped[dict] = mapped_column(JSONB, default=dict)
    
    changed_by: Mapped[str] = mapped_column(String(50), default="FOUNDER")
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ValidationAssumption(Base):
    """
    Giả định kinh doanh & tính điểm rủi ro: Importance * Uncertainty (F1.md §42, §43).
    """
    __tablename__ = "validation_assumptions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    brain_id: Mapped[int] = mapped_column(ForeignKey("brains.id"), index=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), index=True)
    claim_id: Mapped[Optional[int]] = mapped_column(ForeignKey("structured_claims.id"), nullable=True, index=True)

    category: Mapped[str] = mapped_column(String(50), default=AssumptionCategory.CUSTOMER.value, index=True)
    statement: Mapped[str] = mapped_column(Text)
    
    importance: Mapped[int] = mapped_column(Integer, default=3)   # 1-5
    uncertainty: Mapped[int] = mapped_column(Integer, default=3)  # 1-5
    impact: Mapped[int] = mapped_column(Integer, default=3)       # 1-5
    risk_score: Mapped[int] = mapped_column(Integer, default=9, index=True) # importance * uncertainty (1-25)

    source: Mapped[str] = mapped_column(String(100), default="FOUNDER_CHAT")
    status: Mapped[str] = mapped_column(String(50), default=AssumptionStatus.UNTESTED.value, index=True)
    confidence: Mapped[float] = mapped_column(Float, default=0.5)
    owner: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ValidationHypothesis(Base):
    """
    Hypothesis testable chuẩn 5 thành phần: Action + Target + Metric + Threshold + Timeframe (F1.md §44, §45).
    """
    __tablename__ = "validation_hypotheses"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    brain_id: Mapped[int] = mapped_column(ForeignKey("brains.id"), index=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), index=True)
    assumption_id: Mapped[int] = mapped_column(ForeignKey("validation_assumptions.id"), index=True)

    action: Mapped[str] = mapped_column(Text)
    target_segment: Mapped[str] = mapped_column(String(255))
    metric: Mapped[str] = mapped_column(String(255))
    threshold: Mapped[str] = mapped_column(String(255))
    timeframe_days: Mapped[int] = mapped_column(Integer, default=7)

    statement: Mapped[str] = mapped_column(Text) # IF Action FOR Target THEN Metric REACH Threshold WITHIN Timeframe
    quality_gate_passed: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[str] = mapped_column(String(50), default="DRAFT") # DRAFT, READY, TESTING, VALIDATED, INVALIDATED

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ValidationExperiment(Base):
    """
    Smallest useful experiment để thu bằng chứng (F1.md §46).
    """
    __tablename__ = "validation_experiments"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    brain_id: Mapped[int] = mapped_column(ForeignKey("brains.id"), index=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), index=True)
    hypothesis_id: Mapped[int] = mapped_column(ForeignKey("validation_hypotheses.id"), index=True)

    experiment_type: Mapped[str] = mapped_column(String(50), default=ExperimentType.CUSTOMER_INTERVIEW.value, index=True)
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    smallest_useful_scope: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    success_threshold: Mapped[str] = mapped_column(String(255))
    budget_amount: Mapped[float] = mapped_column(Float, default=0.0)
    duration_days: Mapped[int] = mapped_column(Integer, default=7)
    
    status: Mapped[str] = mapped_column(String(50), default="DRAFT", index=True) # DRAFT, SCHEDULED, RUNNING, COMPLETED, CANCELLED
    start_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    end_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    results_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ValidationEvidence(Base):
    """
    Bằng chứng thực tế thu thập từ thị trường/khách hàng (F1.md §47).
    """
    __tablename__ = "validation_evidence"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    brain_id: Mapped[int] = mapped_column(ForeignKey("brains.id"), index=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), index=True)
    
    assumption_id: Mapped[Optional[int]] = mapped_column(ForeignKey("validation_assumptions.id"), nullable=True, index=True)
    hypothesis_id: Mapped[Optional[int]] = mapped_column(ForeignKey("validation_hypotheses.id"), nullable=True, index=True)
    experiment_id: Mapped[Optional[int]] = mapped_column(ForeignKey("validation_experiments.id"), nullable=True, index=True)

    evidence_type: Mapped[str] = mapped_column(String(50), default=EvidenceType.FOUNDER_BELIEF.value, index=True)
    source_type: Mapped[str] = mapped_column(String(100))
    source_ref: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    observation: Mapped[str] = mapped_column(Text)
    metric_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    metric_value: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    relationship: Mapped[str] = mapped_column(String(50), default=EvidenceRelationship.SUPPORTS.value, index=True)
    confidence: Mapped[float] = mapped_column(Float, default=0.5)
    attachments_jsonb: Mapped[list] = mapped_column(JSONB, default=list)

    captured_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ValidationReview(Base):
    """
    Đánh giá của AI hoặc Human Expert (F1.md §48, §49, §55).
    """
    __tablename__ = "validation_reviews"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    brain_id: Mapped[int] = mapped_column(ForeignKey("brains.id"), index=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), index=True)
    hypothesis_id: Mapped[Optional[int]] = mapped_column(ForeignKey("validation_hypotheses.id"), nullable=True, index=True)

    review_provider_type: Mapped[str] = mapped_column(String(50), default=ReviewProviderType.AI.value, index=True)
    reviewer_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    
    verdict: Mapped[str] = mapped_column(String(50), default=ReviewVerdict.TEST_MORE.value, index=True)
    confidence_score: Mapped[float] = mapped_column(Float, default=0.5)
    
    supported_points: Mapped[list] = mapped_column(JSONB, default=list)
    challenged_points: Mapped[list] = mapped_column(JSONB, default=list)
    missing_evidence: Mapped[list] = mapped_column(JSONB, default=list)
    critical_risks: Mapped[list] = mapped_column(JSONB, default=list)
    recommended_next_action: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    human_review_recommended: Mapped[bool] = mapped_column(Boolean, default=False)
    
    raw_report: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ValidationDecision(Base):
    """
    Quyết định chính thức của Founder / Decision Owner (F1.md §13, §64).
    """
    __tablename__ = "validation_decisions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    brain_id: Mapped[int] = mapped_column(ForeignKey("brains.id"), index=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), index=True)
    review_id: Mapped[Optional[int]] = mapped_column(ForeignKey("validation_reviews.id"), nullable=True)

    ai_recommendation: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    human_expert_review: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    
    founder_decision: Mapped[str] = mapped_column(String(50), default=FounderDecisionEnum.PROCEED.value, index=True)
    rationale: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    risks_acknowledged: Mapped[list] = mapped_column(JSONB, default=list)
    
    decided_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    decided_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class DimensionState(Base):
    """
    State Vector đa chiều của từng Dimension trong Dự án (F1.md §9, §10).
    """
    __tablename__ = "dimension_states"
    __table_args__ = (
        UniqueConstraint("project_id", "dimension", name="uq_dimension_state_project_dim"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), index=True)

    dimension: Mapped[str] = mapped_column(String(50), index=True)
    pillar: Mapped[str] = mapped_column(String(50), default=FeasibilityPillar.DESIRABILITY.value)
    
    state: Mapped[str] = mapped_column(String(50), default=DimensionStateEnum.UNKNOWN.value, index=True)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ProjectStageHistory(Base):
    """
    Lịch sử chuyển dịch Stage của Dự án (F1.md §50, §65).
    """
    __tablename__ = "project_stage_history"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), index=True)

    from_stage: Mapped[str] = mapped_column(String(50))
    to_stage: Mapped[str] = mapped_column(String(50))
    transition_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    approved_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class CustomerContact(Base):
    """
    Khách hàng / Đối tượng phỏng vấn (F3.md §8, §22).
    """
    __tablename__ = "validation_customer_contacts"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), index=True)

    name: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(50), default=CustomerRoleEnum.USER.value, index=True)
    segment: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    company: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    contact_info: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class CustomerInterviewSession(Base):
    """
    Phiên phỏng vấn khách hàng thực tế (F3.md §7, §8).
    """
    __tablename__ = "validation_interview_sessions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), index=True)
    contact_id: Mapped[Optional[int]] = mapped_column(ForeignKey("validation_customer_contacts.id"), nullable=True)

    role: Mapped[str] = mapped_column(String(50), default=CustomerRoleEnum.USER.value)
    segment: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    interview_date: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    duration_minutes: Mapped[int] = mapped_column(Integer, default=30)

    raw_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    transcript: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    session_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    referral_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class VerbatimQuote(Base):
    """
    Trích dẫn nguyên văn bất biến (F3.md §9, §10, §11).
    """
    __tablename__ = "validation_verbatim_quotes"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), index=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("validation_interview_sessions.id"), index=True)

    raw_quote: Mapped[str] = mapped_column(Text)  # Immutable quote
    interpretation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # Editable interpretation
    interpretation_actor: Mapped[str] = mapped_column(String(50), default="AI")  # AI or FOUNDER
    
    tags_jsonb: Mapped[list] = mapped_column(JSONB, default=list)  # TIME, COST, EMOTION, BEHAVIOR, ALTERNATIVE, WTP, ROOT_CAUSE, CONSEQUENCE
    buying_signal_level: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # LEVEL_1_INTEREST ... LEVEL_5_STRONG_PROOF
    
    linked_assumption_id: Mapped[Optional[int]] = mapped_column(ForeignKey("validation_assumptions.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ProblemSeverityScorecard(Base):
    """
    Bảng chấm điểm nỗi đau 50 điểm (F2.md §4, §5).
    """
    __tablename__ = "validation_problem_scorecards"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), index=True)

    frequency_score: Mapped[int] = mapped_column(Integer, default=5)
    severity_score: Mapped[int] = mapped_column(Integer, default=5)
    alternatives_score: Mapped[int] = mapped_column(Integer, default=5)
    wtp_score: Mapped[int] = mapped_column(Integer, default=5)
    market_potential_score: Mapped[int] = mapped_column(Integer, default=5)
    total_score: Mapped[int] = mapped_column(Integer, default=25)

    evidence_quality: Mapped[str] = mapped_column(String(50), default="UNVERIFIED")  # UNVERIFIED, FOUNDER_ESTIMATE, EVIDENCE_BACKED
    evidence_refs_jsonb: Mapped[list] = mapped_column(JSONB, default=list)
    
    interpretation_result: Mapped[str] = mapped_column(String(50), default="BELOW_RECOMMENDED_THRESHOLD")
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class PainPattern(Base):
    """
    Phát hiện mẫu lặp từ khám nghiệm dữ liệu (F3.md §13, §14).
    """
    __tablename__ = "validation_pain_patterns"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), index=True)

    cluster_type: Mapped[str] = mapped_column(String(50), default=AutopsyClusterType.PATTERN.value, index=True)
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    frequency_count: Mapped[int] = mapped_column(Integer, default=1)
    quote_refs_jsonb: Mapped[list] = mapped_column(JSONB, default=list)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class EarlyAdopterCandidate(Base):
    """
    Ứng viên Early Adopter với tín hiệu hành động cao (F3.md §24).
    """
    __tablename__ = "validation_early_adopters"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), index=True)
    contact_id: Mapped[int] = mapped_column(ForeignKey("validation_customer_contacts.id"), index=True)

    pain_strength: Mapped[str] = mapped_column(String(50), default="HIGH")
    urgency: Mapped[str] = mapped_column(String(50), default="HIGH")
    buying_signal: Mapped[str] = mapped_column(String(50), default=BuyingSignalLevelEnum.LEVEL_3_WTP.value)
    willingness_to_change: Mapped[str] = mapped_column(String(50), default="HIGH")
    current_alternative: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    evidence_refs_jsonb: Mapped[list] = mapped_column(JSONB, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

