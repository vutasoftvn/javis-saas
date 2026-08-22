"""Định nghĩa THẬT — moved từ agent_runtime/{sessions,events,permissions}/models.py
(2026-08-22). agent_runtime/*/models.py giờ chỉ re-export từ đây (đảo chiều shim)."""
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from cosa_core.db.base import Base
from db.snowflake_model import SnowflakeIDMixin


class AgentRun(SnowflakeIDMixin, Base):
    """Audit and state record for an agent execution run."""
    __tablename__ = "agent_runs"
    __table_args__ = {"schema": "agent_runtime"}

    workspace_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("core.workspaces.id"), index=True, nullable=False)
    company_id: Mapped[Optional[int]] = mapped_column(BigInteger, index=True, nullable=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("core.users.id"), index=True, nullable=False)
    conversation_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True, index=True)
    parent_run_id: Mapped[Optional[int]] = mapped_column(
        BigInteger,
        ForeignKey("agent_runtime.agent_runs.id", name="fk_agent_runs_parent_run_id"),
        nullable=True,
        index=True,
    )
    outcome_run_id: Mapped[Optional[int]] = mapped_column(BigInteger, ForeignKey("runtime_ops.outcome_runs.id", use_alter=True), nullable=True, index=True)

    agent_key: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    job_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    project_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True, index=True)
    runtime: Mapped[str] = mapped_column(String(50), default="mock", nullable=False)
    runtime_version: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    runtime_session_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    provider: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    model: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="created", nullable=False)  # created, running, completed, failed, cancelled, awaiting_approval, retrying, fallback
    permission_profile: Mapped[str] = mapped_column(String(50), default="read_only", nullable=False)

    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    latency_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    input_tokens: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    output_tokens: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    estimated_cost: Mapped[Optional[float]] = mapped_column(nullable=True)
    budget_jsonb: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    error_code: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    error_message: Mapped[Optional[Text]] = mapped_column(Text, nullable=True)
    metadata_jsonb: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)


class AgentEventRecord(SnowflakeIDMixin, Base):
    """Audit log of sequential events emitted during an agent run."""
    __tablename__ = "agent_events"
    __table_args__ = {"schema": "agent_runtime"}

    run_id: Mapped[Optional[int]] = mapped_column(BigInteger, ForeignKey("agent_runtime.agent_runs.id"), index=True, nullable=True)
    company_id: Mapped[Optional[int]] = mapped_column(BigInteger, index=True, nullable=True)
    plan_id: Mapped[Optional[int]] = mapped_column(BigInteger, index=True, nullable=True)
    step_id: Mapped[Optional[int]] = mapped_column(BigInteger, index=True, nullable=True)
    actor_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    actor_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    tool_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    status: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    sequence: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    agent_key: Mapped[str] = mapped_column(String(100), nullable=False)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)  # run_started, thought, tool_started, tool_completed, error...
    event_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    payload_jsonb: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    runtime_event_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    parent_event_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)


class AgentToolCall(SnowflakeIDMixin, Base):
    """Audit record of a specific tool invocation made by an agent."""
    __tablename__ = "agent_tool_calls"
    __table_args__ = {"schema": "agent_runtime"}

    run_id: Mapped[Optional[int]] = mapped_column(BigInteger, ForeignKey("agent_runtime.agent_runs.id"), index=True, nullable=True)
    plan_id: Mapped[Optional[int]] = mapped_column(BigInteger, index=True, nullable=True)
    step_id: Mapped[Optional[int]] = mapped_column(BigInteger, index=True, nullable=True)
    agent_key: Mapped[str] = mapped_column(String(100), nullable=False)
    tool_name: Mapped[str] = mapped_column(String(100), nullable=False)
    risk_level: Mapped[str] = mapped_column(String(20), default="low", nullable=False)  # low, medium, high, critical
    input_jsonb: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    output_jsonb: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="success", nullable=False)  # success, error, blocked, approval_pending
    approval_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True, index=True)

    # Observation & Provenance fields
    resource_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    resource_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    capability: Mapped[Optional[str]] = mapped_column(String(150), nullable=True, index=True)
    source_version: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    content_hash: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    provenance_jsonb: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    latency_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)


class AgentApproval(SnowflakeIDMixin, Base):
    """Approval request generated when an agent attempts an action requiring human authorization."""
    __tablename__ = "agent_approvals"
    __table_args__ = {"schema": "agent_runtime"}

    workspace_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("core.workspaces.id"), index=True, nullable=False)
    company_id: Mapped[Optional[int]] = mapped_column(BigInteger, index=True, nullable=True)
    requested_by_agent: Mapped[str] = mapped_column(String(100), nullable=False)
    run_id: Mapped[Optional[int]] = mapped_column(BigInteger, ForeignKey("agent_runtime.agent_runs.id"), nullable=True, index=True)

    action_type: Mapped[str] = mapped_column(String(100), nullable=False)  # write_activity, send_email, update_stage, close_deal
    tool_name: Mapped[str] = mapped_column(String(100), nullable=False)
    input_preview_jsonb: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    risk_level: Mapped[str] = mapped_column(String(20), default="medium", nullable=False)  # low, medium, high, critical
    status: Mapped[str] = mapped_column(String(50), default="pending", nullable=False)  # pending, approved, rejected, expired, executed, cancelled

    # Action Center extended fields
    capability: Mapped[Optional[str]] = mapped_column(String(150), nullable=True, index=True)
    resource_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    resource_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    simulation_result_jsonb: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    idempotency_key: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    is_strong_approval: Mapped[bool] = mapped_column(default=False, nullable=False)

    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    reviewed_by: Mapped[Optional[int]] = mapped_column(BigInteger, ForeignKey("core.users.id"), nullable=True)
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    execution_result_jsonb: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
