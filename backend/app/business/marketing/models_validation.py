from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any, List

from sqlalchemy import String, Boolean, DateTime, ForeignKey, BigInteger, Text, Integer, Float, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import Base
from app.core.snowflake import generate_snowflake_id


class EpistemicStatus(str, Enum):
    FACT = "fact"
    EVIDENCE = "evidence"
    INFERENCE = "inference"
    ASSUMPTION = "assumption"


class KnowledgeOrigin(str, Enum):
    FOUNDER = "founder"
    AI_GENERATED = "ai_generated"
    CUSTOMER = "customer"
    CRM = "crm"
    ANALYTICS = "analytics"
    EXPERIMENT = "experiment"
    DOCUMENT = "document"


class ConfidenceLevel(str, Enum):
    UNKNOWN = "unknown"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class AssumptionCategory(str, Enum):
    CUSTOMER = "customer"
    PROBLEM = "problem"
    SOLUTION = "solution"
    VALUE_PROPOSITION = "value_proposition"
    POSITIONING = "positioning"
    OFFER = "offer"
    PRICING = "pricing"
    CHANNEL = "channel"
    CONVERSION = "conversion"
    RETENTION = "retention"
    BUSINESS_MODEL = "business_model"


class AssumptionStatus(str, Enum):
    UNTESTED = "untested"
    TESTING = "testing"
    SUPPORTED = "supported"
    PARTIALLY_SUPPORTED = "partially_supported"
    CONTRADICTED = "contradicted"
    INCONCLUSIVE = "inconclusive"
    ARCHIVED = "archived"


class EvidenceSourceType(str, Enum):
    CUSTOMER_INTERVIEW = "customer_interview"
    SURVEY = "survey"
    CRM = "crm"
    ANALYTICS = "analytics"
    LANDING_PAGE = "landing_page"
    CAMPAIGN = "campaign"
    EXPERIMENT = "experiment"
    DOCUMENT = "document"
    FOUNDER_OBSERVATION = "founder_observation"


class EvidenceStrength(str, Enum):
    WEAK = "weak"
    MEDIUM = "medium"
    STRONG = "strong"


class KnowledgeStatement(Base):
    """
    Epistemic Knowledge Statement (§6, §7 in E3.md).
    Phân loại rõ: Fact, Evidence, Inference, Assumption.
    """
    __tablename__ = "knowledge_statements"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    brain_id: Mapped[int] = mapped_column(ForeignKey("brains.id"), index=True)
    project_id: Mapped[Optional[int]] = mapped_column(ForeignKey("projects.id"), nullable=True, index=True)

    statement: Mapped[str] = mapped_column(Text)
    epistemic_status: Mapped[str] = mapped_column(String(50), default=EpistemicStatus.ASSUMPTION.value, index=True)
    origin: Mapped[str] = mapped_column(String(50), default=KnowledgeOrigin.AI_GENERATED.value)
    confidence: Mapped[str] = mapped_column(String(50), default=ConfidenceLevel.LOW.value)
    
    evidence_ids: Mapped[List[str]] = mapped_column(JSONB, default=list)
    meta_data: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Assumption(Base):
    """
    Business Assumption (§12 - §16 in E3.md).
    Criticality = Impact (1-5) * Uncertainty (1-5).
    """
    __tablename__ = "assumptions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    brain_id: Mapped[int] = mapped_column(ForeignKey("brains.id"), index=True)
    project_id: Mapped[Optional[int]] = mapped_column(ForeignKey("projects.id"), nullable=True, index=True)
    canvas_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)

    category: Mapped[str] = mapped_column(String(50), default=AssumptionCategory.CUSTOMER.value, index=True)
    statement: Mapped[str] = mapped_column(Text)
    
    impact: Mapped[int] = mapped_column(Integer, default=3)
    uncertainty: Mapped[int] = mapped_column(Integer, default=3)
    criticality: Mapped[int] = mapped_column(Integer, default=9, index=True)  # impact * uncertainty (1-25)
    
    confidence: Mapped[str] = mapped_column(String(50), default=ConfidenceLevel.LOW.value)
    status: Mapped[str] = mapped_column(String(50), default=AssumptionStatus.UNTESTED.value, index=True)
    
    evidence_ids: Mapped[List[str]] = mapped_column(JSONB, default=list)
    experiment_ids: Mapped[List[str]] = mapped_column(JSONB, default=list)
    rationale: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Evidence(Base):
    """
    Market & Customer Evidence (§33, §34 in E3.md).
    Liên kết dữ liệu thực tế hỗ trợ/phản bác các Assumption.
    """
    __tablename__ = "evidence"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    brain_id: Mapped[int] = mapped_column(ForeignKey("brains.id"), index=True)
    project_id: Mapped[Optional[int]] = mapped_column(ForeignKey("projects.id"), nullable=True, index=True)

    source_type: Mapped[str] = mapped_column(String(50), default=EvidenceSourceType.FOUNDER_OBSERVATION.value, index=True)
    source_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    statement: Mapped[str] = mapped_column(Text)
    supports_assumption_ids: Mapped[List[str]] = mapped_column(JSONB, default=list)
    contradicts_assumption_ids: Mapped[List[str]] = mapped_column(JSONB, default=list)
    strength: Mapped[str] = mapped_column(String(50), default=EvidenceStrength.MEDIUM.value)
    
    meta_data: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    collected_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class CanvasRevision(Base):
    """
    Ground Truth Canvas Revision History (§41 in E3.md).
    Lưu vết thay đổi khi có evidence/learning mới cập nhật Canvas.
    """
    __tablename__ = "canvas_revisions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    brain_id: Mapped[int] = mapped_column(ForeignKey("brains.id"), index=True)
    project_id: Mapped[Optional[int]] = mapped_column(ForeignKey("projects.id"), nullable=True, index=True)
    canvas_type: Mapped[str] = mapped_column(String(100), index=True)  # customer_research, product_marketing, offer, brand

    status: Mapped[str] = mapped_column(String(50), default="approved")  # pending_review, approved, rejected
    changed_fields: Mapped[List[str]] = mapped_column(JSONB, default=list)
    previous_snapshot: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    new_snapshot: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    reason: Mapped[str] = mapped_column(Text)
    evidence_ids: Mapped[List[str]] = mapped_column(JSONB, default=list)
    approved_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class CustomerInterview(Base):
    """
    Structured Customer Interview (§35 in E3.md).
    Trích xuất tín hiệu khách hàng (Pain signals, Objections, Willingness-to-pay, Quotes)
    và tự động sinh Evidence.
    """
    __tablename__ = "customer_interviews"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    brain_id: Mapped[int] = mapped_column(ForeignKey("brains.id"), index=True)
    project_id: Mapped[Optional[int]] = mapped_column(ForeignKey("projects.id"), nullable=True, index=True)
    contact_id: Mapped[Optional[int]] = mapped_column(ForeignKey("contacts.id"), nullable=True, index=True)

    customer_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    segment: Mapped[str] = mapped_column(String(255), default="ICP Target")
    interview_date: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    questions: Mapped[List[Dict[str, Any]]] = mapped_column(JSONB, default=list)
    pains: Mapped[List[str]] = mapped_column(JSONB, default=list)
    alternatives: Mapped[List[str]] = mapped_column(JSONB, default=list)
    objections: Mapped[List[str]] = mapped_column(JSONB, default=list)
    willingness_to_pay: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    notable_quotes: Mapped[List[str]] = mapped_column(JSONB, default=list)
    
    evidence_ids: Mapped[List[str]] = mapped_column(JSONB, default=list)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class MarketingAttribution(Base):
    """
    Marketing Attribution Model (§58, §59 in E3.md).
    Liên kết: Lead -> Experiment -> Assumption.
    """
    __tablename__ = "marketing_attributions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    contact_id: Mapped[Optional[int]] = mapped_column(ForeignKey("contacts.id"), nullable=True, index=True)
    lead_id: Mapped[Optional[int]] = mapped_column(ForeignKey("sales_leads.id"), nullable=True, index=True)
    
    campaign_id: Mapped[Optional[int]] = mapped_column(ForeignKey("marketing_campaigns.id"), nullable=True, index=True)
    experiment_id: Mapped[Optional[int]] = mapped_column(ForeignKey("marketing_experiments.id"), nullable=True, index=True)
    variant_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    utm_source: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    utm_medium: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    utm_campaign: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    utm_content: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    utm_term: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

