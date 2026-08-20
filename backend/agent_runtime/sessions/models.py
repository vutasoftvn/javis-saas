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
    outcome_run_id: Mapped[Optional[int]] = mapped_column(BigInteger, ForeignKey("outcome_runs.id", use_alter=True), nullable=True, index=True)

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
