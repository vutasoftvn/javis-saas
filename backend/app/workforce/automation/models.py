from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import Base
from app.db.snowflake_model import SnowflakeIDMixin


class AutomationDefinition(SnowflakeIDMixin, Base):
    """Catalog of available automations within COSA."""
    __tablename__ = "automation_definitions"

    automation_key: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    domain: Mapped[str] = mapped_column(String(50), nullable=False)  # system, sales, marketing, finance, legal
    provider: Mapped[str] = mapped_column(String(50), default="n8n", nullable=False)
    provider_workflow_ref: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    risk_level: Mapped[str] = mapped_column(String(20), default="low", nullable=False)
    approval_mode: Mapped[str] = mapped_column(String(50), default="none", nullable=False)  # none, required, policy_based
    input_schema_jsonb: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    output_schema_jsonb: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    __table_args__ = (
        UniqueConstraint("automation_key", name="uq_automation_definitions_key"),
    )


class AutomationRun(SnowflakeIDMixin, Base):
    """Audit log of execution runs dispatched to an external automation provider."""
    __tablename__ = "automation_runs"

    workspace_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("workspaces.id"), index=True, nullable=False)
    company_id: Mapped[Optional[int]] = mapped_column(BigInteger, index=True, nullable=True)
    automation_key: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    provider: Mapped[str] = mapped_column(String(50), default="n8n", nullable=False)
    provider_execution_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)

    agent_run_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True, index=True)
    approval_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True, index=True)

    status: Mapped[str] = mapped_column(String(50), default="running", nullable=False)  # running, succeeded, failed, cancelled
    risk_level: Mapped[str] = mapped_column(String(20), default="low", nullable=False)
    idempotency_key: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    payload_jsonb: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    result_jsonb: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    error_code: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    error_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    __table_args__ = (
        UniqueConstraint(
            "workspace_id",
            "idempotency_key",
            name="uq_automation_runs_workspace_idempotency",
        ),
    )


class AutomationCallback(SnowflakeIDMixin, Base):
    """Log of incoming webhook callbacks received from external automation providers."""
    __tablename__ = "automation_callbacks"

    run_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("automation_runs.id"), index=True, nullable=False)
    provider_execution_id: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    signature: Mapped[str] = mapped_column(String(255), nullable=False)
    verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    payload_jsonb: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    __table_args__ = (
        UniqueConstraint("run_id", "signature", name="uq_automation_callbacks_run_signature"),
    )
