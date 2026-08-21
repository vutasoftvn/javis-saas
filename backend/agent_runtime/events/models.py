from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from db.base_class import Base
from db.snowflake_model import SnowflakeIDMixin


class AgentEventRecord(SnowflakeIDMixin, Base):
    """Audit log of sequential events emitted during an agent run."""
    __tablename__ = "agent_events"

    run_id: Mapped[Optional[int]] = mapped_column(BigInteger, ForeignKey("agent_runs.id"), index=True, nullable=True)
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
