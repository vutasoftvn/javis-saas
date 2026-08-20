from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import Base
from app.db.snowflake_model import SnowflakeIDMixin


class AgentToolCall(SnowflakeIDMixin, Base):
    """Audit record of a specific tool invocation made by an agent."""
    __tablename__ = "agent_tool_calls"

    run_id: Mapped[Optional[int]] = mapped_column(BigInteger, ForeignKey("agent_runs.id"), index=True, nullable=True)
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

    workspace_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("workspaces.id"), index=True, nullable=False)
    company_id: Mapped[Optional[int]] = mapped_column(BigInteger, index=True, nullable=True)
    requested_by_agent: Mapped[str] = mapped_column(String(100), nullable=False)
    run_id: Mapped[Optional[int]] = mapped_column(BigInteger, ForeignKey("agent_runs.id"), nullable=True, index=True)

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

    reviewed_by: Mapped[Optional[int]] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=True)
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    execution_result_jsonb: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
