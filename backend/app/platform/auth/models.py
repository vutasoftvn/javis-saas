from datetime import datetime
from typing import Optional

from sqlalchemy import String, Boolean, DateTime, ForeignKey, BigInteger, func, UniqueConstraint, Text, Integer, Numeric, Float
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column, relationship
from pgvector.sqlalchemy import Vector

from app.db.base_class import Base
from app.db.snowflake_model import SnowflakeIDMixin

class User(SnowflakeIDMixin, Base):
    __tablename__ = "users"

    email: Mapped[Optional[str]] = mapped_column(String(255), unique=True, index=True, nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(20), unique=True, index=True, nullable=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=True) # nullable for passwordless/oauth later
    display_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="active")
    platform_user_id: Mapped[Optional[str]] = mapped_column(String(36), unique=True, index=True, nullable=True) # Supabase Central UUID
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # Relationships
    workspaces: Mapped[list["WorkspaceMember"]] = relationship(back_populates="user")

class Workspace(SnowflakeIDMixin, Base):
    __tablename__ = "workspaces"

    name: Mapped[str] = mapped_column(String(255))
    # G2 P0.5 / G3 §10.2: new workspaces used to default to S5_OPERATE_GROWTH
    # (steady-state operating stage) instead of a genesis/day-0 stage. Existing
    # rows are unaffected by a column-default change — do not backfill them.
    # Note: this is a standalone literal, deliberately NOT unified with
    # ProjectStageEnum/StartupStageEnum (which use a different S0-S6 naming
    # scheme on Project.project_stage, a different field/model) — that
    # taxonomy unification is Phase 1D's job (Stage Operating Engine), not P0.
    company_stage: Mapped[str] = mapped_column(String(50), default="S0_GENESIS")
    platform_company_id: Mapped[Optional[str]] = mapped_column(String(36), unique=True, index=True, nullable=True) # Supabase Central UUID
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    members: Mapped[list["WorkspaceMember"]] = relationship(back_populates="workspace")
    brains: Mapped[list["Brain"]] = relationship(back_populates="workspace")

class WorkspaceMember(SnowflakeIDMixin, Base):
    __tablename__ = "workspace_members"

    workspace_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("workspaces.id"), index=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), index=True)
    role: Mapped[str] = mapped_column(String(50), default="member") # admin, member
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    workspace: Mapped["Workspace"] = relationship(back_populates="members")
    user: Mapped["User"] = relationship(back_populates="workspaces")
