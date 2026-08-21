from datetime import datetime
from typing import Optional, List

from sqlalchemy import String, Boolean, DateTime, ForeignKey, BigInteger, func, UniqueConstraint, Text, Integer, Numeric, Float, Index, text
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column, relationship, object_session
from pgvector.sqlalchemy import Vector

from db.base_class import Base
from core.snowflake import generate_snowflake_id

class Project(Base):
    __tablename__ = "projects"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    brain_id: Mapped[int] = mapped_column(ForeignKey("brains.id"), index=True)
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    phase: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    current_gate: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="active")
    owner_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    project_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # STRATEGIC, NEW_BUSINESS, PRODUCT, GROWTH, OPERATIONAL, TECHNICAL, EXPERIMENT, COMPLIANCE
    strategic_priority: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # P0, P1, P2, etc.
    founder_attention_budget: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # hours/week
    portfolio_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True, index=True)
    active_stage_id: Mapped[Optional[int]] = mapped_column(ForeignKey("mvp_stages.id", use_alter=True), nullable=True, index=True)
    start_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    end_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    project_stage: Mapped[str] = mapped_column(String(50), default="S1_PROBLEM_VALIDATION", index=True)  # S0_EXPLORE, S1_PROBLEM_VALIDATION, S2_SOLUTION_VALIDATION, S3_BUSINESS_VALIDATION, S4_GO_TO_MARKET, S5_OPERATE_GROWTH, S6_SCALE_GOVERN
    stage_started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    stage_goal: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    critical_constraints: Mapped[dict] = mapped_column(JSONB, default=list)
    exit_criteria_jsonb: Mapped[dict] = mapped_column(JSONB, default=dict)
    stage_metadata: Mapped[dict] = mapped_column(JSONB, default=dict)
    platform_project_id: Mapped[Optional[str]] = mapped_column(String(36), unique=True, index=True, nullable=True) # Supabase Central UUID
    sync_status: Mapped[str] = mapped_column(String(50), default="synced", index=True) # synced, pending_sync, sync_error
    last_synced_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class MvpStage(Base):
    __tablename__ = "mvp_stages"
    __table_args__ = (
        UniqueConstraint("project_id", "sequence_no", name="uq_mvp_stage_project_sequence"),
        Index("ix_mvp_stage_workspace_project_status", "workspace_id", "project_id", "status"),
        Index("uq_mvp_stage_one_active", "project_id", unique=True, postgresql_where=text("status = 'ACTIVE'")),
    )
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    brain_id: Mapped[int] = mapped_column(ForeignKey("brains.id"), index=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), index=True)
    sequence_no: Mapped[int] = mapped_column(Integer)
    title: Mapped[str] = mapped_column(String(255))
    hypothesis: Mapped[str] = mapped_column(Text)
    scope_jsonb: Mapped[dict] = mapped_column(JSONB, default=dict)
    exit_criteria_jsonb: Mapped[dict] = mapped_column(JSONB, default=dict)
    status: Mapped[str] = mapped_column(String(24), default="DRAFT")  # DRAFT, CONFIRMED, ACTIVE, COMPLETED, STOPPED
    # {template_id: version_no} snapshot recorded at activation; reset/edits afterward never change it.
    template_snapshot_jsonb: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    activated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class ProjectClassification(Base):
    __tablename__ = "project_classifications"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    project_type: Mapped[str] = mapped_column(String(50))  # STRATEGIC, NEW_BUSINESS, PRODUCT, GROWTH, OPERATIONAL, TECHNICAL, EXPERIMENT, COMPLIANCE
    strategic_depth: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # high, medium, low
    uncertainty_level: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # high, medium, low
    risk_level: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # high, medium, low
    research_required: Mapped[bool] = mapped_column(Boolean, default=False)
    external_evidence_required: Mapped[bool] = mapped_column(Boolean, default=False)
    internal_context_required: Mapped[bool] = mapped_column(Boolean, default=False)
    recommended_methodologies: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    human_required_areas: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    rationale: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    confidence_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    classified_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class ProjectPestelImpact(Base):
    """Ma trận tác động PESTEL lên từng Dự án trong Danh mục (Project PESTEL Impact Matrix - Spec §24)."""
    __tablename__ = "project_pestel_impacts"
    __table_args__ = (
        UniqueConstraint("project_id", "pestel_item_id", name="uix_project_pestel_impact"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    pestel_item_id: Mapped[int] = mapped_column(ForeignKey("pestel_items.id", ondelete="CASCADE"), index=True)
    impact_type: Mapped[str] = mapped_column(String(50), default="POSITIVE")  # POSITIVE, NEGATIVE, NEUTRAL
    impact_magnitude: Mapped[str] = mapped_column(String(50), default="MEDIUM")  # HIGH, MEDIUM, LOW
    impact_analysis: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    mitigation_or_leverage: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


# ==========================================
# mCOSA V12 — Portfolio SWOT, Options & Synergies (Sprint 7)
# ==========================================

class StageTransitionAudit(Base):
    """Nhật ký thẩm định chuyển giai đoạn (Stage Gate Audit)."""
    __tablename__ = "stage_transition_audits"
    
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), index=True)
    
    from_stage: Mapped[str] = mapped_column(String(50))
    to_stage: Mapped[str] = mapped_column(String(50))
    
    readiness_score: Mapped[float] = mapped_column(Float, default=0.0) # 0.0 -> 1.0 (>= 0.70 là Passed)
    audit_status: Mapped[str] = mapped_column(String(50), default="REJECTED") # APPROVED | CONDITIONALLY_APPROVED | REJECTED
    
    passed_criteria: Mapped[dict] = mapped_column(JSONB, default=list) # List[Dict]
    missing_criteria: Mapped[dict] = mapped_column(JSONB, default=list) # List[Dict]
    detected_risks: Mapped[dict] = mapped_column(JSONB, default=list) # List[Dict]
    
    audited_by_agent: Mapped[str] = mapped_column(String(100), default="Stage Gate Auditor Agent")
    recommendation_note: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    @property
    def strong_areas(self) -> List[str]:
        return [c.get("title", c.get("id", "")) for c in (self.passed_criteria or [])]

    @property
    def _critical_risk_messages(self) -> List[str]:
        return [r.get("message", r.get("rule_code", "")) for r in (self.detected_risks or []) if r.get("severity") == "CRITICAL"]

    @property
    def weak_areas(self) -> List[str]:
        if self.audit_status == "REJECTED":
            return []
        return [c.get("title", c.get("id", "")) for c in (self.missing_criteria or [])]

    @property
    def blockers(self) -> List[str]:
        blockers = list(self._critical_risk_messages)
        if self.audit_status == "REJECTED":
            blockers = [c.get("title", c.get("id", "")) for c in (self.missing_criteria or [])] + blockers
        return blockers

    @property
    def recommended_action(self) -> str:
        if self.audit_status == "APPROVED":
            return "ADVANCE"
        if self.audit_status == "CONDITIONALLY_APPROVED":
            return "CONTINUE"

        # REJECTED: xem lịch sử để phân biệt CONTINUE (thử lại) vs PIVOT/STOP (bế tắc lặp lại)
        consecutive_rejected = 1 if self.audit_status == "REJECTED" else 0
        session = object_session(self)
        if session is not None:
            history = (
                session.query(StageTransitionAudit)
                .filter(
                    StageTransitionAudit.project_id == self.project_id,
                    StageTransitionAudit.from_stage == self.from_stage,
                    StageTransitionAudit.to_stage == self.to_stage,
                )
                .order_by(StageTransitionAudit.created_at.desc())
                .all()
            )
            consecutive_rejected = 0
            for a in history:
                if a.audit_status == "REJECTED":
                    consecutive_rejected += 1
                else:
                    break

        if consecutive_rejected >= 3:
            return "STOP" if self._critical_risk_messages else "PIVOT"
        return "CONTINUE"

class PrematureScalingAlert(Base):
    """Cảnh báo rủi ro mở rộng quy mô non trẻ (Anti-Premature Scaling Guardrail)."""
    __tablename__ = "premature_scaling_alerts"
    
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), index=True)
    
    current_stage: Mapped[str] = mapped_column(String(50))
    rule_code: Mapped[str] = mapped_column(String(100)) # E.g., NO_PAID_ADS_IN_S1, NO_SALES_HIRE_IN_S2
    severity: Mapped[str] = mapped_column(String(50), default="WARNING") # CRITICAL | WARNING | INFO
    title: Mapped[str] = mapped_column(String(255))
    message: Mapped[str] = mapped_column(Text)
    
    is_dismissed: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


# ==========================================
# COSA Stage-Aware — 12-Week Year Execution Loop (Phase 5)
# ==========================================
