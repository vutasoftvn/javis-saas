from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from db.base_class import Base
from db.snowflake_model import SnowflakeIDMixin


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ExecutionJob(SnowflakeIDMixin, Base):
    """Bản ghi công việc thực thi cô lập trong sandbox."""
    __tablename__ = "execution_jobs"

    workspace_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("workspaces.id"), index=True, nullable=False)
    brain_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True, index=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), index=True, nullable=False)
    agent_run_id: Mapped[Optional[int]] = mapped_column(BigInteger, ForeignKey("agent_runs.id"), nullable=True, index=True)

    agent_key: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    provider: Mapped[str] = mapped_column(String(50), default="mock", nullable=False)
    sandbox_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    policy_id: Mapped[Optional[int]] = mapped_column(BigInteger, ForeignKey("sandbox_policies.id"), nullable=True)

    status: Mapped[str] = mapped_column(String(50), default="queued", nullable=False, index=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    idempotency_key: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    destroyed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    error_code: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    metadata_jsonb: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    __table_args__ = (
        UniqueConstraint("workspace_id", "idempotency_key", name="uq_execution_jobs_ws_idempotency"),
    )


class ExecutionStep(SnowflakeIDMixin, Base):
    """Bản ghi các bước / câu lệnh thực thi trong một execution job."""
    __tablename__ = "execution_steps"

    job_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("execution_jobs.id"), index=True, nullable=False)
    sequence: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    step_type: Mapped[str] = mapped_column(String(50), default="command", nullable=False)  # upload, command, download

    command: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="completed", nullable=False)
    exit_code: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    stdout_excerpt: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    stderr_excerpt: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class SandboxPolicyRecord(SnowflakeIDMixin, Base):
    """Bản ghi chính sách tài nguyên, mạng và quyền của sandbox."""
    __tablename__ = "sandbox_policies"

    workspace_id: Mapped[Optional[int]] = mapped_column(BigInteger, ForeignKey("workspaces.id"), index=True, nullable=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    agent_type: Mapped[str] = mapped_column(String(50), default="generic", nullable=False)

    network_policy_jsonb: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    filesystem_policy_jsonb: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    command_policy_jsonb: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    credential_policy_jsonb: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    resource_limit_jsonb: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    timeout_seconds: Mapped[int] = mapped_column(Integer, default=300, nullable=False)
    approval_policy: Mapped[str] = mapped_column(String(50), default="auto", nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)
