from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from db.base_class import Base
from db.snowflake_model import SnowflakeIDMixin


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class DelegationJob(SnowflakeIDMixin, Base):
    """Durable coordination state for one RunStep delegation attempt."""

    __tablename__ = "delegation_jobs"

    workspace_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("core.workspaces.id"), nullable=False, index=True
    )
    run_step_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("runtime_ops.run_steps.id"), nullable=False, index=True
    )
    root_agent_run_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("agent_runtime.agent_runs.id"), nullable=False, index=True
    )
    parent_agent_run_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("agent_runtime.agent_runs.id"), nullable=False, index=True
    )
    child_agent_run_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, ForeignKey("agent_runtime.agent_runs.id"), nullable=True, index=True
    )

    attempt_no: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    provider_kind: Mapped[str] = mapped_column(String(50), nullable=False)
    provider_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    profile_id: Mapped[str] = mapped_column(String(100), nullable=False)
    runtime_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="queued", server_default="queued", index=True
    )
    provider_handle_jsonb: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    idempotency_key: Mapped[str] = mapped_column(String(255), nullable=False)

    available_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, index=True
    )
    next_poll_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    max_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=3, server_default="3")

    claimed_by: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    lease_token: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    lease_expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    heartbeat_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    cancel_requested_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    reserved_cost_usd: Mapped[Decimal] = mapped_column(
        Numeric(12, 6), nullable=False, default=Decimal("0"), server_default="0"
    )
    reserved_tool_calls: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    reserved_steps: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )

    result_jsonb: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    error_code: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )

    __table_args__ = (
        UniqueConstraint("run_step_id", "attempt_no", name="uq_delegation_job_step_attempt"),
        UniqueConstraint(
            "workspace_id", "idempotency_key", name="uq_delegation_job_workspace_idempotency"
        ),
        Index("ix_delegation_jobs_status_available", "status", "available_at"),
        Index("ix_delegation_jobs_status_next_poll", "status", "next_poll_at"),
        {"schema": "agent_runtime"},
    )
