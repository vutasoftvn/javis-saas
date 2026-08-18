from datetime import datetime
from typing import Optional, List
from sqlalchemy import (
    String, Boolean, DateTime, ForeignKey, BigInteger, UniqueConstraint,
    Text, Integer, Numeric, Float, Index, text
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base
from app.core.snowflake import generate_snowflake_id


class SourceDocument(Base):
    """
    Nguồn văn bản pháp lý, quyết định, tài liệu hội thảo hoặc tài liệu chính sách chính thức.
    """
    __tablename__ = "policy_source_documents"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    brain_id: Mapped[int] = mapped_column(ForeignKey("brains.id"), index=True)
    title: Mapped[str] = mapped_column(String(255))
    authority: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)  # Cơ quan ban hành: BKHCN, Bộ TT&TT, UBND TP...
    document_type: Mapped[str] = mapped_column(String(50), default="PROGRAM_GUIDE")  # LAW, DECREE, CIRCULAR, PROGRAM_GUIDE, PRESENTATION, OTHER
    document_number: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)  # Số hiệu văn bản
    issued_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    source_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    file_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)  # SHA-256
    verification_status: Mapped[str] = mapped_column(String(50), default="UNVERIFIED")  # VERIFIED, UNVERIFIED, REJECTED
    verification_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    verified_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class SourceSnapshot(Base):
    """
    Snapshot nội dung thô của tài liệu nguồn phục vụ audit diff và trích xuất AI.
    """
    __tablename__ = "policy_source_snapshots"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    source_document_id: Mapped[int] = mapped_column(ForeignKey("policy_source_documents.id"), index=True)
    content_raw: Mapped[str] = mapped_column(Text)
    extracted_metadata_jsonb: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class PolicyProgram(Base):
    """
    Chương trình chính sách, quỹ, gói voucher, credit hạ tầng hoặc hỗ trợ tài chính.
    """
    __tablename__ = "policy_programs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    brain_id: Mapped[int] = mapped_column(ForeignKey("brains.id"), index=True)
    name: Mapped[str] = mapped_column(String(255))
    code: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    program_type: Mapped[str] = mapped_column(String(50), default="GRANT")  # GRANT, LOAN_SUPPORT, INTEREST_SUBSIDY, VOUCHER, CLOUD_CREDIT, INFRASTRUCTURE, EXPERT_SUPPORT, PRIVATE_CAPITAL, OTHER
    legal_basis: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    authority: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    geography: Mapped[Optional[str]] = mapped_column(String(100), default="NATIONAL")  # NATIONAL, LOCAL_HANOI, LOCAL_HCM, LOCAL_DANANG, GLOBAL...
    
    # Target Criteria
    company_types: Mapped[dict] = mapped_column(JSONB, default=list)  # ["STARTUP", "SPIN_OFF", "SCIENCE_TECH_ENTERPRISE", "INNOVATIVE_SME", "DIGITAL_SME"]
    project_stages: Mapped[dict] = mapped_column(JSONB, default=list)  # ["IDEA", "POC", "PROTOTYPE", "MVP", "MARKET_VALIDATION", "ACCELERATION", "SCALE_UP", "GROWTH"]
    trl_min: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # 1..9
    industries: Mapped[dict] = mapped_column(JSONB, default=list)  # ["AI", "SAAS", "BIOTECH", "GREENTECH", "HARDWARE", "AGRITECH", "FINTECH", "ALL"]
    
    # Financials & Matching
    funding_min: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    funding_max: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    currency: Mapped[str] = mapped_column(String(10), default="VND")
    matching_fund_pct: Mapped[Optional[float]] = mapped_column(Float, default=0.0)  # % vốn đối ứng yêu cầu (ví dụ: 30.0%)
    eligible_costs: Mapped[dict] = mapped_column(JSONB, default=list)  # ["RD_SALARY", "EQUIPMENT", "TESTING", "IP_REGISTRATION", "CLOUD_HOSTING", "MARKETING_PILOT"]
    
    # Lifecycle & Provenance
    status: Mapped[str] = mapped_column(String(50), default="DRAFT")  # DRAFT, ENACTED, UPCOMING, ACTIVE, CLOSED, EXPIRED, SUSPENDED, UNKNOWN
    verification_status: Mapped[str] = mapped_column(String(50), default="PENDING_FOUNDER_VERIFICATION")  # PENDING_FOUNDER_VERIFICATION, SOURCE_CLAIMED_CURRENT, VERIFIED_ACTIVE, VERIFIED_ENACTED, VERIFIED_CLOSED, REJECTED_SOURCE_DATA, DRAFT_WATCHLIST
    matching_mode: Mapped[str] = mapped_column(String(20), default="soft")  # soft, strict
    publish_to_matching: Mapped[bool] = mapped_column(Boolean, default=True)
    source_claim: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    claimed_values_jsonb: Mapped[dict] = mapped_column(JSONB, default=dict)
    source_document_id: Mapped[Optional[int]] = mapped_column(ForeignKey("policy_source_documents.id"), nullable=True, index=True)
    source_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    application_window_start: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    application_window_end: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    last_verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ProgramRound(Base):
    """
    Đợt tiếp nhận hồ sơ của chương trình.
    """
    __tablename__ = "policy_program_rounds"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    program_id: Mapped[int] = mapped_column(ForeignKey("policy_programs.id"), index=True)
    round_name: Mapped[str] = mapped_column(String(255))
    start_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    end_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="ACTIVE")  # UPCOMING, ACTIVE, CLOSED
    budget_total: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class EligibilityRule(Base):
    """
    Quy tắc điều kiện chi tiết (Hard vs Soft) của chương trình.
    """
    __tablename__ = "policy_eligibility_rules"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    program_id: Mapped[int] = mapped_column(ForeignKey("policy_programs.id"), index=True)
    rule_type: Mapped[str] = mapped_column(String(20), default="HARD")  # HARD (bắt buộc), SOFT (cộng điểm)
    category: Mapped[str] = mapped_column(String(50), default="LEGAL")  # LEGAL, TECH_TRL, FINANCIAL, IP, MARKET, TEAM
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    field_path: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)  # ví dụ: "project.trl", "company.type", "project.matching_fund_confirmed"
    operator: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # GTE, LTE, EQ, IN, CONTAINS, EXISTS
    expected_value_jsonb: Mapped[dict] = mapped_column(JSONB, default=dict)
    source_document_id: Mapped[Optional[int]] = mapped_column(ForeignKey("policy_source_documents.id"), nullable=True)
    legal_reference: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)  # ví dụ: "Điều 23 Khoản 2 NĐ 268/2025"
    weight: Mapped[float] = mapped_column(Float, default=1.0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ProjectStageAssessment(Base):
    """
    Lịch sử và trạng thái xác định Stage / Company Type cho từng Project.
    """
    __tablename__ = "project_stage_assessments"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), index=True)
    company_type: Mapped[str] = mapped_column(String(50), default="STARTUP")  # STARTUP, SPIN_OFF, SCIENCE_TECH_ENTERPRISE, INNOVATIVE_SME, DIGITAL_SME, OTHER
    stage: Mapped[str] = mapped_column(String(50), default="MVP")  # IDEA, POC, PROTOTYPE, MVP, MARKET_VALIDATION, ACCELERATION, SCALE_UP, GROWTH
    ai_suggested_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    ai_suggested_stage: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    ai_confidence_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    is_founder_confirmed: Mapped[bool] = mapped_column(Boolean, default=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class TrlAssessment(Base):
    """
    Đánh giá mức độ sẵn sàng công nghệ (TRL 1-9) gắn với Project và bằng chứng.
    """
    __tablename__ = "project_trl_assessments"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), index=True)
    trl_current: Mapped[int] = mapped_column(Integer, default=3)  # 1..9
    trl_target: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    explanation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    evidence_artifact_id: Mapped[Optional[int]] = mapped_column(ForeignKey("artifacts.id"), nullable=True)
    evidence_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    assessed_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class FundingNeed(Base):
    """
    Nhu cầu vốn và nguồn lực cần thiết của Project.
    """
    __tablename__ = "project_funding_needs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), index=True)
    need_category: Mapped[str] = mapped_column(String(50), default="CASH")  # CASH, CLOUD_CREDIT, INFRASTRUCTURE, VOUCHER, ADVISORY, IP_FILING
    amount_target: Mapped[float] = mapped_column(Float, default=0.0)
    currency: Mapped[str] = mapped_column(String(10), default="VND")
    purpose_description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    co_funding_available: Mapped[float] = mapped_column(Float, default=0.0)
    co_funding_confirmed: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ProjectProgramMatch(Base):
    """
    Kết quả khớp nối cơ hội giữa Project và PolicyProgram.
    """
    __tablename__ = "project_program_matches"
    __table_args__ = (
        UniqueConstraint("project_id", "program_id", name="uq_project_program_match"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), index=True)
    program_id: Mapped[int] = mapped_column(ForeignKey("policy_programs.id"), index=True)
    
    # 3 Separate Evaluative Dimensions
    eligibility_status: Mapped[str] = mapped_column(String(30), default="POTENTIALLY_ELIGIBLE")  # ELIGIBLE, POTENTIALLY_ELIGIBLE, INELIGIBLE, NEEDS_VERIFICATION
    match_score: Mapped[float] = mapped_column(Float, default=0.0)  # 0..100
    readiness_score: Mapped[float] = mapped_column(Float, default=0.0)  # 0..100
    
    # Pipeline Stage
    pipeline_stage: Mapped[str] = mapped_column(String(30), default="MATCHED")  # DISCOVERED, MATCHED, REVIEWING, PREPARING, READY, SUBMITTED, UNDER_REVIEW, APPROVED, REJECTED, CONTRACTED, DISBURSING, REPORTING, COMPLETED
    
    # Explainability & Summary
    passed_rules_count: Mapped[int] = mapped_column(Integer, default=0)
    total_rules_count: Mapped[int] = mapped_column(Integer, default=0)
    ai_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    calculated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class EligibilityEvaluation(Base):
    """
    Chi tiết đánh giá từng điều kiện cụ thể của một lần matching.
    """
    __tablename__ = "project_eligibility_evaluations"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    match_id: Mapped[int] = mapped_column(ForeignKey("project_program_matches.id"), index=True)
    rule_id: Mapped[int] = mapped_column(ForeignKey("policy_eligibility_rules.id"), index=True)
    status: Mapped[str] = mapped_column(String(30), default="PENDING")  # PASSED, FAILED, MISSING_INFO, NEEDS_VERIFICATION
    actual_value_jsonb: Mapped[dict] = mapped_column(JSONB, default=dict)
    ai_explanation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    evidence_artifact_id: Mapped[Optional[int]] = mapped_column(ForeignKey("artifacts.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class MissingRequirement(Base):
    """
    Các điều kiện / minh chứng còn thiếu của Project cho một cơ hội cụ thể.
    """
    __tablename__ = "project_missing_requirements"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), index=True)
    program_id: Mapped[int] = mapped_column(ForeignKey("policy_programs.id"), index=True)
    category: Mapped[str] = mapped_column(String(50), default="EVIDENCE")  # LEGAL, IP, CO_FUNDING, BUDGET, KPI, EVIDENCE
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_resolved: Mapped[bool] = mapped_column(Boolean, default=False)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    linked_task_id: Mapped[Optional[int]] = mapped_column(ForeignKey("tasks.id"), nullable=True)  # Task trong 12WY
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Application(Base):
    """
    Hồ sơ ứng tuyển / Thuyết minh dự án gửi đến một chương trình hỗ trợ.
    """
    __tablename__ = "policy_applications"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    brain_id: Mapped[int] = mapped_column(ForeignKey("brains.id"), index=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), index=True)
    program_id: Mapped[int] = mapped_column(ForeignKey("policy_programs.id"), index=True)
    title: Mapped[str] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(30), default="DRAFT")  # DRAFT, IN_REVIEW, READY, SUBMITTED, APPROVED, REJECTED
    template_version: Mapped[str] = mapped_column(String(50), default="1.0")
    requested_amount: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    co_funding_amount: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    submitted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    submitted_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ApplicationSection(Base):
    """
    Từng phần trong hồ sơ thuyết minh dự án (Bối cảnh, Mục tiêu, Công nghệ, TRL, Đầu ra, Ngân sách...).
    """
    __tablename__ = "policy_application_sections"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    application_id: Mapped[int] = mapped_column(ForeignKey("policy_applications.id"), index=True)
    section_key: Mapped[str] = mapped_column(String(100))  # BACKGROUND, OBJECTIVES, TECHNOLOGY, TRL, OUTPUT_KPIS, WORK_PLAN, COMMERCIALIZATION, BUDGET, TEAM, IP, RISKS
    section_title: Mapped[str] = mapped_column(String(255))
    sequence_no: Mapped[int] = mapped_column(Integer, default=1)
    content_draft: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    content_approved: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_approved: Mapped[bool] = mapped_column(Boolean, default=False)
    missing_fields_jsonb: Mapped[dict] = mapped_column(JSONB, default=list)  # Các trường cần founder điền bổ sung
    approved_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class FundingAward(Base):
    """
    Khoản tài trợ, hỗ trợ hoặc tín dụng ưu đãi đã được phê duyệt và giải ngân cho Project.
    """
    __tablename__ = "project_funding_awards"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    brain_id: Mapped[int] = mapped_column(ForeignKey("brains.id"), index=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), index=True)
    program_id: Mapped[int] = mapped_column(ForeignKey("policy_programs.id"), index=True)
    award_name: Mapped[str] = mapped_column(String(255))
    award_type: Mapped[str] = mapped_column(String(50), default="GRANT")  # GRANT, CLOUD_CREDIT, VOUCHER, PREFERENTIAL_LOAN, INTEREST_SUBSIDY, PRIVATE_CAPITAL
    approved_amount: Mapped[float] = mapped_column(Float, default=0.0)
    cash_amount: Mapped[float] = mapped_column(Float, default=0.0)
    non_cash_value: Mapped[float] = mapped_column(Float, default=0.0)
    matching_required: Mapped[float] = mapped_column(Float, default=0.0)
    matching_actual: Mapped[float] = mapped_column(Float, default=0.0)
    start_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    end_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    restricted_use: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="ACTIVE")  # ACTIVE, COMPLETED, SUSPENDED, TERMINATED
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ComplianceObligation(Base):
    """
    Nghĩa vụ và báo cáo tuân thủ hậu tài trợ.
    """
    __tablename__ = "project_compliance_obligations"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    award_id: Mapped[int] = mapped_column(ForeignKey("project_funding_awards.id"), index=True)
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    due_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="PENDING")  # PENDING, SUBMITTED, ACCEPTED, OVERDUE
    evidence_artifact_id: Mapped[Optional[int]] = mapped_column(ForeignKey("artifacts.id"), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class CostAllocation(Base):
    """
    Phân bổ chi phí phục vụ kiểm tra và cảnh báo chống trùng nguồn hỗ trợ (Double Funding Guard).
    """
    __tablename__ = "project_cost_allocations"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), index=True)
    award_id: Mapped[Optional[int]] = mapped_column(ForeignKey("project_funding_awards.id"), nullable=True)
    application_id: Mapped[Optional[int]] = mapped_column(ForeignKey("policy_applications.id"), nullable=True)
    work_package: Mapped[str] = mapped_column(String(100))  # ví dụ: "MVP Testing", "Cloud Server", "IP Filing"
    period_start: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    period_end: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    cost_category: Mapped[str] = mapped_column(String(50))  # SALARY, HOSTING, MARKETING, LEGAL, HARDWARE
    purpose: Mapped[str] = mapped_column(String(255))
    amount: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class AdminPolicyInbox(Base):
    """
    Hộp thư quản trị chính sách mới phát hiện chờ Admin xác minh và duyệt publish.
    """
    __tablename__ = "admin_policy_inboxes"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    source_title: Mapped[str] = mapped_column(String(255))
    source_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    detected_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    extracted_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    extracted_data_jsonb: Mapped[dict] = mapped_column(JSONB, default=dict)
    ai_confidence: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[str] = mapped_column(String(50), default="PENDING")  # PENDING, VERIFIED, PUBLISHED, REJECTED, DRAFT
    reviewed_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class PolicyProgramClaim(Base):
    """
    Lưu trữ mệnh đề/tuyên bố trích xuất từ tài liệu nguồn (Claim-based architecture)
    nhằm tách biệt 'Nguồn nói gì' khỏi 'COSA đã xác minh gì'.
    """
    __tablename__ = "policy_program_claims"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    program_id: Mapped[int] = mapped_column(ForeignKey("policy_programs.id"), index=True)
    claim_type: Mapped[str] = mapped_column(String(50))  # SUPPORT_AMOUNT, RATE_CAP, DURATION, ELIGIBLE_COSTS, TARGET_COMPANY, APPLICATION_CHANNEL, MATCHING_FUND, OTHER
    claim_key: Mapped[str] = mapped_column(String(100))  # e.g., "funding_max_vnd", "support_ratio", "max_months"
    claim_value: Mapped[str] = mapped_column(Text)  # e.g., "8 tỷ đồng/nhiệm vụ", "50% lãi suất vay thực tế", "6%/năm"
    source_document_id: Mapped[Optional[int]] = mapped_column(ForeignKey("policy_source_documents.id"), nullable=True)
    source_page: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    source_excerpt: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    verified_value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class PolicyVerification(Base):
    """
    Nhật ký và bằng chứng kiểm chứng của Founder hoặc Admin đối với một chương trình/quyền lợi.
    """
    __tablename__ = "policy_verifications"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    program_id: Mapped[int] = mapped_column(ForeignKey("policy_programs.id"), index=True)
    verified_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    verified_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    official_source_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    official_document_id: Mapped[Optional[int]] = mapped_column(ForeignKey("policy_source_documents.id"), nullable=True)
    official_authority: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    result_status: Mapped[str] = mapped_column(String(50))  # VERIFIED_ACTIVE, VERIFIED_ENACTED, VERIFIED_CLOSED, REJECTED_SOURCE_DATA, PENDING_FOUNDER_VERIFICATION
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    diff_jsonb: Mapped[dict] = mapped_column(JSONB, default=dict)  # Các trường đã được sửa so với slide nguồn
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class PolicyChangeProposal(Base):
    """
    Đề xuất thay đổi chính sách phát hiện bởi AI hoặc đề xuất bởi Founder/Admin trước khi áp dụng vào Production Catalog.
    """
    __tablename__ = "policy_change_proposals"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    program_id: Mapped[Optional[int]] = mapped_column(ForeignKey("policy_programs.id"), nullable=True, index=True)
    change_type: Mapped[str] = mapped_column(String(50))  # AMOUNT_CHANGED, ELIGIBILITY_CHANGED, DEADLINE_CHANGED, STATUS_CHANGED, DOCUMENT_CHANGED, LEGAL_BASIS_CHANGED, APPLICATION_CHANNEL_CHANGED, NEW_PROGRAM, PROGRAM_CLOSED
    field_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    old_value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    new_value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source_excerpt: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)  # AI reading confidence (0..1.0)
    ai_model: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    review_status: Mapped[str] = mapped_column(String(30), default="PENDING")  # PENDING, APPROVED, REJECTED
    reviewed_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    review_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    detected_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

