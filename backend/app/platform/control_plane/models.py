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


class Plan(ControlPlaneBase):
    __tablename__ = "plans"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    default_limits: Mapped[Dict[str, Any]] = mapped_column(
        JSONB, nullable=False,
        default=lambda: {"max_projects": 1, "max_seats": 2, "max_scheduled_agents": 1},
    )
    default_features: Mapped[Dict[str, Any]] = mapped_column(
        JSONB, nullable=False,
        default=lambda: {"marketing": True, "crm": True, "finance": False, "custom_domain": False},
    )
    is_public: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class License(SnowflakeIDMixin, ControlPlaneBase):
    __tablename__ = "licenses"
    __table_args__ = (
        Index("ix_licenses_company", "company_id"),
        Index("ix_licenses_key", "license_key"),
    )

    company_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False
    )
    plan_id: Mapped[str] = mapped_column(String(50), ForeignKey("plans.id"), nullable=False)
    license_key: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="active")
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    grace_period_days: Mapped[int] = mapped_column(Integer, nullable=False, default=7)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class CompanyEntitlement(ControlPlaneBase):
    __tablename__ = "company_entitlements"

    company_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("companies.id", ondelete="CASCADE"), primary_key=True
    )
    plan_id: Mapped[str] = mapped_column(String(50), ForeignKey("plans.id"), nullable=False)
    effective_limits: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False)
    effective_features: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False)
    custom_overrides: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    last_issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    snapshot_signature: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class ProjectRegistry(SnowflakeIDMixin, ControlPlaneBase):
    """Central project registry. KHONG con cot `local_project_snowflake`/
    constraint `uq_company_project_local` — du thua tu khi PK trung tam la
    BigInt Snowflake (Quyet dinh 5), thay vi UUID nhu ban `deploy/central_vps
    /init_central_postgres.sql` cu."""

    __tablename__ = "projects_registry"
    __table_args__ = (
        Index("ix_projects_registry_company", "company_id"),
        Index("ix_projects_registry_stage", "current_stage"),
    )

    company_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    industry: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    category: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="active")
    current_stage: Mapped[str] = mapped_column(String(50), nullable=False, default="S0_EXPLORE")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    last_stage_change_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow
    )
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


class ProjectStageHistory(SnowflakeIDMixin, ControlPlaneBase):
    __tablename__ = "project_stage_history"
    __table_args__ = (
        Index("ix_project_stage_history_project", "project_id"),
        Index("ix_project_stage_history_company", "company_id"),
    )

    project_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("projects_registry.id", ondelete="CASCADE"), nullable=False
    )
    company_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False
    )
    from_stage: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    to_stage: Mapped[str] = mapped_column(String(50), nullable=False)
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    duration_seconds: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    change_source: Mapped[Optional[str]] = mapped_column(String(50), default="local_sync")
    # `metadata` la thuoc tinh dung rieng cua SQLAlchemy Declarative — map
    # qua thuoc tinh Python `metadata_json`, ten cot DB van la `metadata`.
    # nullable=True khop nguyen ban SQL goc (`metadata JSONB DEFAULT '{}'::jsonb`,
    # khong co NOT NULL) — phai khai bao dung nullable o day, neu khong
    # `alembic check` o Task 11 se bao lech giua model va migration.
    metadata_json: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        "metadata", JSONB, nullable=True, default=dict
    )


class ProjectOutcome(ControlPlaneBase):
    __tablename__ = "project_outcomes"

    project_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("projects_registry.id", ondelete="CASCADE"), primary_key=True
    )
    company_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False
    )
    first_interview_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    first_experiment_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    mvp_launched_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    first_customer_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    first_revenue_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    has_revenue: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    revenue_band: Mapped[Optional[str]] = mapped_column(String(50), default="0")
    team_size_band: Mapped[Optional[str]] = mapped_column(String(50), default="1-2")
    outcome_updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow
    )


class ProjectMetric(ControlPlaneBase):
    __tablename__ = "project_metrics"

    project_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("projects_registry.id", ondelete="CASCADE"), primary_key=True
    )
    company_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False
    )
    customer_interview_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    experiment_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    validated_assumption_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    invalidated_assumption_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    lead_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    customer_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    active_campaign_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    mvp_release_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_metric_sync_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow
    )


class Program(ControlPlaneBase):
    __tablename__ = "programs"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    partner_name: Mapped[Optional[str]] = mapped_column(String(255), default="SIHUB")
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)


class Cohort(ControlPlaneBase):
    __tablename__ = "cohorts"

    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    program_id: Mapped[str] = mapped_column(String(50), ForeignKey("programs.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    start_date: Mapped[Any] = mapped_column(Date, nullable=False)
    end_date: Mapped[Optional[Any]] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)


class ProgramParticipant(SnowflakeIDMixin, ControlPlaneBase):
    __tablename__ = "program_participants"
    __table_args__ = (
        UniqueConstraint("cohort_id", "company_id", name="uq_cohort_participant"),
        Index("ix_program_participants_cohort", "cohort_id"),
        Index("ix_program_participants_company", "company_id"),
    )

    program_id: Mapped[str] = mapped_column(String(50), ForeignKey("programs.id", ondelete="CASCADE"), nullable=False)
    cohort_id: Mapped[str] = mapped_column(String(100), ForeignKey("cohorts.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("platform_users.id", ondelete="CASCADE"), nullable=False
    )
    company_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False
    )
    enrolled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="active")


class ProjectProgramLink(ControlPlaneBase):
    __tablename__ = "project_program_links"

    project_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("projects_registry.id", ondelete="CASCADE"), primary_key=True
    )
    cohort_id: Mapped[str] = mapped_column(
        String(100), ForeignKey("cohorts.id", ondelete="CASCADE"), primary_key=True
    )
    linked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)


class CompanyWebApp(SnowflakeIDMixin, ControlPlaneBase):
    __tablename__ = "company_web_apps"

    company_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False
    )
    app_type: Mapped[str] = mapped_column(String(50), nullable=False, default="marketing")
    repository_ref: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    deployment_mode: Mapped[str] = mapped_column(String(50), nullable=False, default="cosa_managed")
    current_version: Mapped[Optional[str]] = mapped_column(String(50), default="v1.0.0")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class Domain(SnowflakeIDMixin, ControlPlaneBase):
    __tablename__ = "domains"
    __table_args__ = (Index("ix_domains_hostname", "hostname"),)

    company_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False
    )
    app_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("company_web_apps.id", ondelete="CASCADE"), nullable=False
    )
    hostname: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    domain_type: Mapped[str] = mapped_column(String(50), nullable=False, default="cosa_subdomain")
    verification_status: Mapped[str] = mapped_column(String(50), nullable=False, default="verified")
    ssl_status: Mapped[str] = mapped_column(String(50), nullable=False, default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)


class FormSubmission(SnowflakeIDMixin, ControlPlaneBase):
    __tablename__ = "form_submissions"
    __table_args__ = (Index("ix_form_submissions_company_sync", "company_id", "sync_status"),)

    company_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False
    )
    project_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, ForeignKey("projects_registry.id"), nullable=True
    )
    form_slug: Mapped[str] = mapped_column(String(100), nullable=False)
    payload: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False)
    source_domain: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    ip_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    sync_status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending")
    synced_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


class Deployment(SnowflakeIDMixin, ControlPlaneBase):
    """VPS deployment registry cua Central Control Plane. KHONG duoc nham lan
    voi `app.platform.core.deployment_models.Deployment` (Local Business DB,
    schema `public`, cung ten bang `deployments` nhung khac cot hoan toan) —
    day chinh la va cham ten bang thuc te da verify khien plan nay dua toan
    bo bang control-plane vao schema `control_plane` rieng."""

    __tablename__ = "deployments"

    company_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False
    )
    app_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("company_web_apps.id", ondelete="CASCADE"), nullable=False
    )
    version: Mapped[str] = mapped_column(String(50), nullable=False)
    target_type: Mapped[str] = mapped_column(String(50), nullable=False, default="cosa_shared_vps")
    target_ref: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    hostname: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    build_status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending")
    deployment_status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    deployed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)




