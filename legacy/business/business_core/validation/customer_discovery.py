from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any, List

from sqlalchemy import String, Boolean, DateTime, ForeignKey, BigInteger, Text, Integer, Float, Index, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.base_class import Base
from core.snowflake import generate_snowflake_id
from business_core.validation.enums import BuyingSignalLevelEnum, CustomerRoleEnum, AutopsyClusterType


class CustomerContact(Base):
    """
    Khách hàng / Đối tượng phỏng vấn (F3.md §8, §22).
    """
    __tablename__ = "validation_customer_contacts"
    __table_args__ = {"schema": "validation"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("core.workspaces.id"), index=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("strategy.projects.id"), index=True)

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
    __table_args__ = {"schema": "validation"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("core.workspaces.id"), index=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("strategy.projects.id"), index=True)
    contact_id: Mapped[Optional[int]] = mapped_column(ForeignKey("validation.validation_customer_contacts.id"), nullable=True)

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
    __table_args__ = {"schema": "validation"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("core.workspaces.id"), index=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("strategy.projects.id"), index=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("validation.validation_interview_sessions.id"), index=True)

    raw_quote: Mapped[str] = mapped_column(Text)  # Immutable quote
    interpretation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # Editable interpretation
    interpretation_actor: Mapped[str] = mapped_column(String(50), default="AI")  # AI or FOUNDER
    
    tags_jsonb: Mapped[list] = mapped_column(JSONB, default=list)  # TIME, COST, EMOTION, BEHAVIOR, ALTERNATIVE, WTP, ROOT_CAUSE, CONSEQUENCE
    buying_signal_level: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # LEVEL_1_INTEREST ... LEVEL_5_STRONG_PROOF
    
    linked_assumption_id: Mapped[Optional[int]] = mapped_column(ForeignKey("validation.validation_assumptions.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class ProblemSeverityScorecard(Base):
    """
    Bảng chấm điểm nỗi đau 50 điểm (F2.md §4, §5).
    """
    __tablename__ = "validation_problem_scorecards"
    __table_args__ = {"schema": "validation"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("core.workspaces.id"), index=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("strategy.projects.id"), index=True)

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
    __table_args__ = {"schema": "validation"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("core.workspaces.id"), index=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("strategy.projects.id"), index=True)

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
    __table_args__ = {"schema": "validation"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("core.workspaces.id"), index=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("strategy.projects.id"), index=True)
    contact_id: Mapped[int] = mapped_column(ForeignKey("validation.validation_customer_contacts.id"), index=True)

    pain_strength: Mapped[str] = mapped_column(String(50), default="HIGH")
    urgency: Mapped[str] = mapped_column(String(50), default="HIGH")
    buying_signal: Mapped[str] = mapped_column(String(50), default=BuyingSignalLevelEnum.LEVEL_3_WTP.value)
    willingness_to_change: Mapped[str] = mapped_column(String(50), default="HIGH")
    current_alternative: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    evidence_refs_jsonb: Mapped[list] = mapped_column(JSONB, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
