from datetime import datetime
from typing import Optional, List

from sqlalchemy import String, Boolean, DateTime, ForeignKey, BigInteger, func, UniqueConstraint, Text, Integer, Numeric, Float, Index, text
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column, relationship, object_session
from pgvector.sqlalchemy import Vector

from app.db.base_class import Base
from app.core.snowflake import generate_snowflake_id

class FounderProfile(Base):
    """Hồ sơ năng lực & giới hạn WIP của Founder (Spec §31)."""
    __tablename__ = "founder_profiles"
    __table_args__ = (
        UniqueConstraint("workspace_id", "user_id", name="uix_founder_profile_workspace_user"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    weekly_capacity_hours: Mapped[float] = mapped_column(Float, default=40.0)
    max_active_strategic_projects: Mapped[int] = mapped_column(Integer, default=3)  # WIP Limit §31
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
