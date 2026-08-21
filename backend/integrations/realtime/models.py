from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, String, DateTime, ForeignKey, Text, Numeric, Integer
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from db.base_class import Base
from core.snowflake import generate_snowflake_id


class RealtimeSession(Base):
    """LiveKit realtime voice session (mCOSA V12.1 §36) — Cloud-only MVP (LK-0..LK-3)."""
    __tablename__ = "realtime_sessions"
    __table_args__ = {"schema": "integrations"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    device_type: Mapped[str] = mapped_column(String(20))  # desktop | mobile | web
    transport: Mapped[str] = mapped_column(String(30), default="livekit_cloud")
    model_profile: Mapped[str] = mapped_column(String(50), default="gemini_live")
    room_name: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    status: Mapped[str] = mapped_column(String(20), default="creating")  # creating|active|ended|error
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    ended_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    # Transcript retention default is SAVE_SUMMARY (mCOSA V12.1 §38/§93/§157):
    # raw transcript is never persisted here, only an optional end-of-session
    # summary supplied when the session ends.
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class RealtimeEvent(Base):
    """Structured session/tool/error event log (mCOSA V12.1 §37), distinct
    from the full transcript - persist only what is useful for audit/UX, not
    raw conversation content."""
    __tablename__ = "realtime_events"
    __table_args__ = {"schema": "integrations"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    session_id: Mapped[int] = mapped_column(ForeignKey("integrations.realtime_sessions.id"), index=True)
    event_type: Mapped[str] = mapped_column(String(50))  # SESSION_CONNECTED|SESSION_ERROR|SESSION_ENDED|...
    payload: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class VoiceUsageRecord(Base):
    """Session cost/usage tracking (mCOSA V12.1 §46/§56, spec §82), written
    once at end_session - do not assume voice is free because one layer has
    a free allowance."""
    __tablename__ = "voice_usage_records"
    __table_args__ = {"schema": "integrations"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    session_id: Mapped[int] = mapped_column(ForeignKey("integrations.realtime_sessions.id"), unique=True, index=True)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    duration_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    model_profile: Mapped[str] = mapped_column(String(50))
    # No pricing model wired up yet - left nullable until a real per-provider
    # cost calculation exists rather than guessing a number.
    estimated_cost: Mapped[Optional[float]] = mapped_column(Numeric(10, 4), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
