from datetime import datetime
from typing import Optional, List, Dict, Any

from sqlalchemy import BigInteger, String, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base
from app.core.snowflake import generate_snowflake_id


class Outcome(Base):
    """Mô hình Outcome - Định nghĩa mục tiêu kết quả cần hoàn thành (§127–129)."""
    __tablename__ = "outcomes"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    project_id: Mapped[Optional[int]] = mapped_column(ForeignKey("projects.id"), nullable=True, index=True)
    cycle_id: Mapped[Optional[int]] = mapped_column(ForeignKey("twelve_week_cycles.id"), nullable=True, index=True)
    task_id: Mapped[Optional[int]] = mapped_column(ForeignKey("tasks.id"), nullable=True, index=True)
    function: Mapped[Optional[str]] = mapped_column(String(20), nullable=True, index=True)
    title: Mapped[str] = mapped_column(String(255))
    desired_result: Mapped[str] = mapped_column(Text)
    acceptance_criteria: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    required_artifacts: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    reviewer_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    review_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    validation_rules: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    rework_count: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False, server_default="0")
    requested_by: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    status: Mapped[str] = mapped_column(String(50), default="draft")  # draft, planning, running, waiting_approval, completed, failed, cancelled
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class OutcomeRun(Base):
    """Mô hình OutcomeRun - Thể hiện một phiên thực thi mục tiêu (§132 job state machine)."""
    __tablename__ = "outcome_runs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    outcome_id: Mapped[int] = mapped_column(ForeignKey("outcomes.id"), index=True)
    status: Mapped[str] = mapped_column(String(50), default="queued")  # queued, running, waiting_approval, retry_scheduled, succeeded, failed, cancelled
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class RunStep(Base):
    """Mô hình RunStep - Các bước cụ thể trong một OutcomeRun."""
    __tablename__ = "run_steps"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    run_id: Mapped[int] = mapped_column(ForeignKey("outcome_runs.id"), index=True)
    type: Mapped[str] = mapped_column(String(50), default="action")
    inputs_jsonb: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    expected_output: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    risk_level: Mapped[str] = mapped_column(String(20), default="L0")  # L0, L1, L2, L3, L4
    depends_on_step_ids: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="pending")  # pending, running, waiting_approval, completed, failed, skipped
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class RunEvent(Base):
    """Mô hình RunEvent - Sự kiện bất biến trong vòng đời của OutcomeRun (§127)."""
    __tablename__ = "run_events"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    run_id: Mapped[int] = mapped_column(ForeignKey("outcome_runs.id"), index=True)
    event_type: Mapped[str] = mapped_column(String(100))  # run.created, step.started, step.completed, tool.requested, tool.completed, approval.requested, approval.resolved, artifact.created, run.completed, run.failed
    payload_jsonb: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Artifact(Base):
    """Mô hình Artifact - Sản phẩm đầu ra hữu hình (tài liệu, code, diff, báo cáo)."""
    __tablename__ = "artifacts"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    run_id: Mapped[Optional[int]] = mapped_column(ForeignKey("outcome_runs.id"), nullable=True, index=True)
    execution_job_id: Mapped[Optional[int]] = mapped_column(BigInteger, ForeignKey("execution_jobs.id"), nullable=True, index=True)
    outcome_id: Mapped[Optional[int]] = mapped_column(ForeignKey("outcomes.id"), nullable=True, index=True)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    type: Mapped[str] = mapped_column(String(50))  # document, spreadsheet, code, research_bundle, media, external_action_receipt, dashboard_snapshot
    title: Mapped[str] = mapped_column(String(255))
    local_uri: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    object_storage_uri: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    content_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="draft")  # draft, review, approved, published, superseded
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
