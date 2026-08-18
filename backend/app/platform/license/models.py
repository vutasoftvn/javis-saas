from datetime import datetime
from typing import Optional, Dict, Any

from sqlalchemy import BigInteger, String, DateTime, ForeignKey, Text, Integer, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import Base
from app.core.snowflake import generate_snowflake_id


class WorkReview(Base):
    """Work Review model — Evaluates whether outcome output meets acceptance criteria."""
    __tablename__ = "work_reviews"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    outcome_id: Mapped[int] = mapped_column(ForeignKey("outcomes.id"), index=True)
    reviewer_type: Mapped[str] = mapped_column(String(50))  # SELF_CHECK, FUNCTION_LEAD_REVIEW, COSA_REVIEW, FOUNDER_REVIEW, EXPERT_REVIEW, DETERMINISTIC_VALIDATION
    reviewer_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    result: Mapped[str] = mapped_column(String(50))  # ACCEPTED, REWORK_REQUIRED, ESCALATED
    feedback: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    evidence_refs: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Blocker(Base):
    """Blocker model — Tracks structured operational and cross-function blockers."""
    __tablename__ = "blockers"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    task_id: Mapped[Optional[int]] = mapped_column(ForeignKey("tasks.id"), nullable=True, index=True)
    outcome_id: Mapped[Optional[int]] = mapped_column(ForeignKey("outcomes.id"), nullable=True, index=True)
    cycle_id: Mapped[Optional[int]] = mapped_column(ForeignKey("twelve_week_cycles.id"), nullable=True, index=True)
    weekly_mission_id: Mapped[Optional[int]] = mapped_column(ForeignKey("weekly_commitments.id"), nullable=True, index=True)
    blocker_type: Mapped[str] = mapped_column(String(50))  # MISSING_DEPENDENCY, MISSING_DOCUMENT, FINANCE_EXCEPTION, LEGAL_UNCERTAINTY, TECHNICAL_BLOCK, FOUNDER_DECISION, HUMAN_INPUT
    description: Mapped[str] = mapped_column(Text)
    requested_capability: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    assigned_function: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)  # legal, marketing, sales, tech, finance
    status: Mapped[str] = mapped_column(String(50), default="OPEN")  # OPEN, ROUTED, RESOLVING, RESOLVED, ESCALATED, CANCELLED
    resolution_artifact_id: Mapped[Optional[int]] = mapped_column(ForeignKey("artifacts.id"), nullable=True)
    escalated_to: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


class NeedsYouItem(Base):
    """Needs You overlay model — Single queue for items needing founder/executive action."""
    __tablename__ = "needs_you_items"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    cycle_id: Mapped[Optional[int]] = mapped_column(ForeignKey("twelve_week_cycles.id"), nullable=True, index=True)
    source_type: Mapped[str] = mapped_column(String(50), index=True)  # blocker, approval, pending_approval, email_approval, workflow_approval, review, finance_exception, legal_exception, recovery
    source_id: Mapped[int] = mapped_column(BigInteger, index=True)
    priority: Mapped[str] = mapped_column(String(20), default="P1")  # P0, P1, P2
    reason: Mapped[str] = mapped_column(Text)
    requested_action: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    due_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="OPEN")  # OPEN, SNOOZED, RESOLVED, CANCELLED
    snooze_until: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


class Handoff(Base):
    """Structured Handoff model — Explicit collaboration artifact between functions."""
    __tablename__ = "handoffs"
    __table_args__ = (
        UniqueConstraint("workspace_id", "idempotency_key", name="uq_handoffs_workspace_idempotency_key"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    cycle_id: Mapped[Optional[int]] = mapped_column(ForeignKey("twelve_week_cycles.id"), nullable=True, index=True)
    weekly_mission_id: Mapped[Optional[int]] = mapped_column(ForeignKey("weekly_commitments.id"), nullable=True, index=True)
    from_function: Mapped[str] = mapped_column(String(50), index=True)
    to_function: Mapped[str] = mapped_column(String(50), index=True)
    source_task_id: Mapped[Optional[int]] = mapped_column(ForeignKey("tasks.id"), nullable=True, index=True)
    target_task_id: Mapped[Optional[int]] = mapped_column(ForeignKey("tasks.id"), nullable=True, index=True)
    handoff_type: Mapped[str] = mapped_column(String(50))  # REQUEST_INPUT, TRANSFER_ARTIFACT, ASK_REVIEW, ASK_DECISION, REPORT_BLOCKER, HANDOFF_TO_NEXT_FUNCTION
    requested_action: Mapped[str] = mapped_column(Text)
    artifact_refs: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    decision_refs: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    due_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    idempotency_key: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="PENDING")  # PENDING, ACCEPTED, REJECTED, COMPLETED
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class RuntimeCheckpoint(Base):
    """Runtime Checkpoint model — Operational state snapshot for crash recovery and resume."""
    __tablename__ = "runtime_checkpoints"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    cycle_id: Mapped[Optional[int]] = mapped_column(ForeignKey("twelve_week_cycles.id"), nullable=True, index=True)
    weekly_mission_id: Mapped[Optional[int]] = mapped_column(ForeignKey("weekly_commitments.id"), nullable=True, index=True)
    sequence: Mapped[int] = mapped_column(Integer, default=1)
    work_item_states: Mapped[Optional[dict]] = mapped_column(JSONB, default=dict)
    dependency_state: Mapped[Optional[dict]] = mapped_column(JSONB, default=dict)
    pending_approvals: Mapped[Optional[dict]] = mapped_column(JSONB, default=dict)
    pending_needs_you: Mapped[Optional[dict]] = mapped_column(JSONB, default=dict)
    active_executors: Mapped[Optional[dict]] = mapped_column(JSONB, default=dict)
    checkpoint_reason: Mapped[str] = mapped_column(String(100))  # PERIODIC, WORK_ITEM_STATE_CHANGE, APPROVAL_CREATED, BEFORE_EXTERNAL_ACTION, SESSION_END, DEVICE_SLEEP, ERROR_RECOVERY
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
