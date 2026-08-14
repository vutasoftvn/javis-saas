from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import Base
from app.db.snowflake_model import SnowflakeIDMixin


class AgentRun(SnowflakeIDMixin, Base):
    """Audit and state record for an agent execution run."""
    __tablename__ = "agent_runs"

    workspace_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("workspaces.id"), index=True, nullable=False)
    company_id: Mapped[Optional[int]] = mapped_column(BigInteger, index=True, nullable=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), index=True, nullable=False)
    conversation_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True, index=True)
    parent_run_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True, index=True)

    agent_key: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    runtime: Mapped[str] = mapped_column(String(50), default="mock", nullable=False)
    runtime_version: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    runtime_session_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    provider: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    model: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="completed", nullable=False)  # completed, failed, cancelled, awaiting_approval, partial
    permission_profile: Mapped[str] = mapped_column(String(50), default="read_only", nullable=False)

    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    latency_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    input_tokens: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    output_tokens: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    estimated_cost: Mapped[Optional[float]] = mapped_column(nullable=True)

    error_code: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    metadata_jsonb: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)


class AgentEventRecord(SnowflakeIDMixin, Base):
    """Audit log of sequential events emitted during an agent run."""
    __tablename__ = "agent_events"

    run_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("agent_runs.id"), index=True, nullable=False)
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

    run_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("agent_runs.id"), index=True, nullable=False)
    agent_key: Mapped[str] = mapped_column(String(100), nullable=False)
    tool_name: Mapped[str] = mapped_column(String(100), nullable=False)
    risk_level: Mapped[str] = mapped_column(String(20), default="low", nullable=False)  # low, medium, high, critical
    input_jsonb: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    output_jsonb: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="success", nullable=False)  # success, error, blocked, approval_pending
    approval_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True, index=True)

    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    latency_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)


class AgentApproval(SnowflakeIDMixin, Base):
    """Approval request generated when an agent attempts an action requiring human authorization."""
    __tablename__ = "agent_approvals"

    workspace_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("workspaces.id"), index=True, nullable=False)
    company_id: Mapped[Optional[int]] = mapped_column(BigInteger, index=True, nullable=True)
    requested_by_agent: Mapped[str] = mapped_column(String(100), nullable=False)
    run_id: Mapped[Optional[int]] = mapped_column(BigInteger, ForeignKey("agent_runs.id"), nullable=True, index=True)

    action_type: Mapped[str] = mapped_column(String(100), nullable=False)  # write_activity, send_email, update_stage, close_deal
    tool_name: Mapped[str] = mapped_column(String(100), nullable=False)
    input_preview_jsonb: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    risk_level: Mapped[str] = mapped_column(String(20), default="medium", nullable=False)  # low, medium, high, critical
    status: Mapped[str] = mapped_column(String(50), default="pending", nullable=False)  # pending, approved, rejected, expired, executed, cancelled

    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    reviewed_by: Mapped[Optional[int]] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=True)
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    execution_result_jsonb: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
