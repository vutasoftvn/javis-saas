from datetime import datetime
from typing import Optional, List

from sqlalchemy import String, Boolean, DateTime, ForeignKey, BigInteger, func, UniqueConstraint, Text, Integer, Numeric, Float, Index, text
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column, relationship, object_session
from pgvector.sqlalchemy import Vector

from app.db.base_class import Base
from app.core.snowflake import generate_snowflake_id

class Initiative(Base):
    __tablename__ = "initiatives"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    brain_id: Mapped[int] = mapped_column(ForeignKey("brains.id"), index=True)
    project_id: Mapped[Optional[int]] = mapped_column(ForeignKey("projects.id"), nullable=True)
    offering_id: Mapped[Optional[int]] = mapped_column(ForeignKey("offerings.id"), nullable=True, index=True)
    title: Mapped[str] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(50), default="active")
    owner_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class InitiativeKeyResultLink(Base):
    __tablename__ = "initiative_key_result_links"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    initiative_id: Mapped[int] = mapped_column(ForeignKey("initiatives.id"), index=True)
    key_result_id: Mapped[int] = mapped_column(ForeignKey("key_results.id"), index=True)
    contribution_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
