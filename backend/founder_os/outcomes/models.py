from datetime import datetime
from typing import Optional, List, Dict, Any

from sqlalchemy import BigInteger, String, DateTime, ForeignKey, Integer, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.base_class import Base
from core.snowflake import generate_snowflake_id


class Outcome(Base):
    """Mô hình Outcome - Định nghĩa mục tiêu kết quả cần hoàn thành (§127–129)."""
    __tablename__ = "outcomes"
    __table_args__ = {"schema": "runtime_ops"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("core.workspaces.id"), index=True)
    project_id: Mapped[Optional[int]] = mapped_column(ForeignKey("strategy.projects.id"), nullable=True, index=True)
    cycle_id: Mapped[Optional[int]] = mapped_column(ForeignKey("operating.twelve_week_cycles.id"), nullable=True, index=True)
    task_id: Mapped[Optional[int]] = mapped_column(ForeignKey("operating.tasks.id"), nullable=True, index=True)
    function: Mapped[Optional[str]] = mapped_column(String(20), nullable=True, index=True)
    title: Mapped[str] = mapped_column(String(255))
    desired_result: Mapped[str] = mapped_column(Text)
    acceptance_criteria: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    required_artifacts: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    reviewer_id: Mapped[Optional[int]] = mapped_column(ForeignKey("core.users.id"), nullable=True, index=True)
    review_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    validation_rules: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    rework_count: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False, server_default="0")
    requested_by: Mapped[int] = mapped_column(ForeignKey("core.users.id"), index=True)
    status: Mapped[str] = mapped_column(String(50), default="draft")  # draft, planning, running, waiting_approval, completed, failed, cancelled
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class OutcomeRun(Base):
    """Mô hình OutcomeRun - Thể hiện một phiên thực thi mục tiêu (§132 job state machine)."""
    __tablename__ = "outcome_runs"
    __table_args__ = {"schema": "runtime_ops"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    outcome_id: Mapped[int] = mapped_column(ForeignKey("runtime_ops.outcomes.id"), index=True)
    agent_run_id: Mapped[Optional[int]] = mapped_column(BigInteger, ForeignKey("agent_runtime.agent_runs.id", use_alter=True), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(50), default="queued")  # queued, running, waiting_approval, retry_scheduled, succeeded, failed, cancelled
    verification_status: Mapped[str] = mapped_column(String(50), default="UNKNOWN")  # UNKNOWN, VERIFIED, PARTIAL, FAILED
    verification_jsonb: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class RunStep(Base):
    """Mô hình RunStep - Các bước cụ thể trong một OutcomeRun."""
    __tablename__ = "run_steps"
    __table_args__ = {"schema": "runtime_ops"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    run_id: Mapped[int] = mapped_column(ForeignKey("runtime_ops.outcome_runs.id"), index=True)
    type: Mapped[str] = mapped_column(String(50), default="action")
    inputs_jsonb: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    expected_output: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    risk_level: Mapped[str] = mapped_column(String(20), default="R0", server_default="R0")  # R0, R1, R2, R3, R4
    depends_on_step_ids: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="pending")  # pending, running, waiting_approval, completed, failed, skipped
    assigned_agent_profile_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    assigned_runtime: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    delegated_run_id: Mapped[Optional[int]] = mapped_column(
        BigInteger,
        ForeignKey("agent_runtime.agent_runs.id", use_alter=True),
        nullable=True,
        index=True,
    )
    result_jsonb: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class RunEvent(Base):
    """Mô hình RunEvent - Sự kiện bất biến trong vòng đời của OutcomeRun (§127)."""
    __tablename__ = "run_events"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    run_id: Mapped[int] = mapped_column(ForeignKey("runtime_ops.outcome_runs.id"), index=True)
    event_type: Mapped[str] = mapped_column(String(100))  # run.created, step.started, step.completed, tool.requested, tool.completed, approval.requested, approval.resolved, artifact.created, run.completed, run.failed
    payload_jsonb: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    # Added nullable first so the existing direct event writers remain deployable.
    # Phase C Task 2 backfills both fields and routes writes through the atomic
    # event allocator before enforcing NOT NULL.
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    event_key: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("run_id", "sequence", name="uq_run_events_run_sequence"),
        UniqueConstraint("run_id", "event_key", name="uq_run_events_run_event_key"),
        {"schema": "runtime_ops"},
    )


class Artifact(Base):
    """Mô hình Artifact - Sản phẩm đầu ra hữu hình (tài liệu, code, diff, báo cáo)."""
    __tablename__ = "artifacts"
    __table_args__ = {"schema": "runtime_ops"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    run_id: Mapped[Optional[int]] = mapped_column(ForeignKey("runtime_ops.outcome_runs.id"), nullable=True, index=True)
    execution_job_id: Mapped[Optional[int]] = mapped_column(BigInteger, ForeignKey("agent_runtime.execution_jobs.id"), nullable=True, index=True)
    outcome_id: Mapped[Optional[int]] = mapped_column(ForeignKey("runtime_ops.outcomes.id"), nullable=True, index=True)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("core.workspaces.id"), index=True)
    scope_snapshot_jsonb: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    type: Mapped[str] = mapped_column(String(50))  # document, spreadsheet, code, research_bundle, media, external_action_receipt, dashboard_snapshot
    title: Mapped[str] = mapped_column(String(255))
    local_uri: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    object_storage_uri: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    content_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="draft")  # draft, review, approved, published, superseded
    created_by: Mapped[int] = mapped_column(ForeignKey("core.users.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
