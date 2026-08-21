"""ORM models của COSA Central Control Plane (Quyết định 2).

Nguồn: infra/supabase/migrations/001_initial_central_control_plane.sql
(bien the BigInt Snowflake — thang PK). Da bo: cot `local_project_snowflake`
va constraint `uq_company_project_local` o `projects_registry` (du thua khi
PK trung tam da la BigInt Snowflake). Da chuyen: moi bang vao schema Postgres
`control_plane` (xem db.py) thay vi `public`.
"""
from datetime import datetime
from typing import Optional, Dict, Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.snowflake_model import SnowflakeIDMixin
from app.platform.control_plane.db import ControlPlaneBase


class PlatformUser(SnowflakeIDMixin, ControlPlaneBase):
    """Central platform user — Custom JWT (HS256), KHONG dung Supabase Auth."""

    __tablename__ = "platform_users"
    __table_args__ = (
        CheckConstraint("email IS NOT NULL OR phone IS NOT NULL", name="chk_email_or_phone"),
        Index("ix_platform_users_email", "email", postgresql_where=text("email IS NOT NULL")),
        Index("ix_platform_users_phone", "phone", postgresql_where=text("phone IS NOT NULL")),
        Index("ix_platform_users_status", "status"),
    )

    email: Mapped[Optional[str]] = mapped_column(String(255), unique=True, nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(50), unique=True, nullable=True)
    hashed_password: Mapped[str] = mapped_column(Text, nullable=False)
    full_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    avatar_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_platform_admin: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="active")
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class Company(SnowflakeIDMixin, ControlPlaneBase):
    __tablename__ = "companies"
    __table_args__ = (
        Index("ix_companies_slug", "slug"),
        Index("ix_companies_status", "status"),
    )

    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    logo_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    industry: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    country_code: Mapped[Optional[str]] = mapped_column(String(10), default="VN")
    created_by: Mapped[Optional[int]] = mapped_column(
        BigInteger, ForeignKey("platform_users.id"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


class CompanyMembership(SnowflakeIDMixin, ControlPlaneBase):
    __tablename__ = "company_memberships"
    __table_args__ = (
        UniqueConstraint("company_id", "user_id", name="uq_company_user"),
        Index("ix_company_memberships_user", "user_id"),
        Index("ix_company_memberships_company", "company_id"),
    )

    company_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("platform_users.id", ondelete="CASCADE"), nullable=False
    )
    platform_role: Mapped[str] = mapped_column(String(50), nullable=False, default="member")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )
