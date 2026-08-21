from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any, List

from sqlalchemy import String, Boolean, DateTime, ForeignKey, BigInteger, Text, Integer, Float, Index, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.base_class import Base
from core.snowflake import generate_snowflake_id
from business_core.validation.enums import AssumptionCategory, AssumptionStatus, ExperimentType, EvidenceType, EvidenceRelationship, ReviewProviderType, ReviewVerdict, FounderDecisionEnum


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
