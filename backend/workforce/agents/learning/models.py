"""SQLAlchemy model for Job Outcomes & Verification records."""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from db.base_class import Base
from db.snowflake_model import SnowflakeIDMixin


class JobOutcome(SnowflakeIDMixin, Base):
    """Outcome record tracking expected vs actual results for learning and verification."""

    __tablename__ = "job_outcomes"

    workspace_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("workspaces.id"), index=True, nullable=False)
    run_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("agent_runs.id"), index=True, nullable=False)
    metric: Mapped[str] = mapped_column(String(100), nullable=False)
    expected_jsonb: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    actual_jsonb: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    source_ref: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
