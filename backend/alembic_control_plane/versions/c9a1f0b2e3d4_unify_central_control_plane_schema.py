"""unify central control plane schema (Quyet dinh 2)

Hop nhat infra/supabase/migrations/001_initial_central_control_plane.sql
(BigInt Snowflake PK - thang) va deploy/central_vps/init_central_postgres.sql
(UUID PK - bi loai) thanh 1 nguon Alembic duy nhat. Toan bo bang nam trong
schema Postgres `control_plane` (khong phai `public`) de tranh trung ten voi
Local Business DB (vi du: bang `deployments`).

Revision ID: c9a1f0b2e3d4
Revises:
Create Date: 2026-08-21 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "c9a1f0b2e3d4"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

CONTROL_PLANE_SCHEMA = "control_plane"


def upgrade() -> None:
    # An toan gap doi: env.py da CREATE SCHEMA truoc khi track version, o day
    # lap lai idempotent de migration nay tu no cung dung duoc neu chay qua
    # 1 duong khac.
    op.execute(f"CREATE SCHEMA IF NOT EXISTS {CONTROL_PLANE_SCHEMA}")

    # ---- Section 1: Platform Identity & Company Registry ----
    op.create_table(
        "platform_users",
        sa.Column("id", sa.BigInteger(), autoincrement=False, nullable=False),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("phone", sa.String(length=50), nullable=True),
        sa.Column("hashed_password", sa.Text(), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=True),
        sa.Column("avatar_url", sa.Text(), nullable=True),
        sa.Column("is_platform_admin", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="active"),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
        sa.UniqueConstraint("phone"),
        sa.CheckConstraint("email IS NOT NULL OR phone IS NOT NULL", name="chk_email_or_phone"),
        schema=CONTROL_PLANE_SCHEMA,
    )
    op.create_index("ix_platform_users_id", "platform_users", ["id"], unique=False, schema=CONTROL_PLANE_SCHEMA)
    op.create_index(
        "ix_platform_users_email", "platform_users", ["email"],
        unique=False, schema=CONTROL_PLANE_SCHEMA, postgresql_where=sa.text("email IS NOT NULL"),
    )
    op.create_index(
        "ix_platform_users_phone", "platform_users", ["phone"],
        unique=False, schema=CONTROL_PLANE_SCHEMA, postgresql_where=sa.text("phone IS NOT NULL"),
    )
    op.create_index("ix_platform_users_status", "platform_users", ["status"], unique=False, schema=CONTROL_PLANE_SCHEMA)

    op.create_table(
        "companies",
        sa.Column("id", sa.BigInteger(), autoincrement=False, nullable=False),
        sa.Column("slug", sa.String(length=100), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("logo_url", sa.Text(), nullable=True),
        sa.Column("industry", sa.String(length=100), nullable=True),
        sa.Column("country_code", sa.String(length=10), nullable=True, server_default="VN"),
        sa.Column("created_by", sa.BigInteger(), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
        sa.ForeignKeyConstraint(["created_by"], [f"{CONTROL_PLANE_SCHEMA}.platform_users.id"]),
        schema=CONTROL_PLANE_SCHEMA,
    )
    op.create_index("ix_companies_id", "companies", ["id"], unique=False, schema=CONTROL_PLANE_SCHEMA)
    op.create_index("ix_companies_slug", "companies", ["slug"], unique=False, schema=CONTROL_PLANE_SCHEMA)
    op.create_index("ix_companies_status", "companies", ["status"], unique=False, schema=CONTROL_PLANE_SCHEMA)

    op.create_table(
        "company_memberships",
        sa.Column("id", sa.BigInteger(), autoincrement=False, nullable=False),
        sa.Column("company_id", sa.BigInteger(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("platform_role", sa.String(length=50), nullable=False, server_default="member"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("company_id", "user_id", name="uq_company_user"),
        sa.ForeignKeyConstraint(["company_id"], [f"{CONTROL_PLANE_SCHEMA}.companies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], [f"{CONTROL_PLANE_SCHEMA}.platform_users.id"], ondelete="CASCADE"),
        schema=CONTROL_PLANE_SCHEMA,
    )
    op.create_index("ix_company_memberships_id", "company_memberships", ["id"], unique=False, schema=CONTROL_PLANE_SCHEMA)
    op.create_index("ix_company_memberships_user", "company_memberships", ["user_id"], unique=False, schema=CONTROL_PLANE_SCHEMA)
    op.create_index("ix_company_memberships_company", "company_memberships", ["company_id"], unique=False, schema=CONTROL_PLANE_SCHEMA)

    # ---- Section 2: Commercial, Plans, Licenses & Entitlements ----
    op.create_table(
        "plans",
        sa.Column("id", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "default_limits", postgresql.JSONB(astext_type=sa.Text()), nullable=False,
            server_default=sa.text("""'{"max_projects": 1, "max_seats": 2, "max_scheduled_agents": 1}'::jsonb"""),
        ),
        sa.Column(
            "default_features", postgresql.JSONB(astext_type=sa.Text()), nullable=False,
            server_default=sa.text(
                """'{"marketing": true, "crm": true, "finance": false, "custom_domain": false}'::jsonb"""
            ),
        ),
        sa.Column("is_public", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
        schema=CONTROL_PLANE_SCHEMA,
    )

    op.create_table(
        "licenses",
        sa.Column("id", sa.BigInteger(), autoincrement=False, nullable=False),
        sa.Column("company_id", sa.BigInteger(), nullable=False),
        sa.Column("plan_id", sa.String(length=50), nullable=False),
        sa.Column("license_key", sa.String(length=100), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="active"),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("grace_period_days", sa.Integer(), nullable=False, server_default="7"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("license_key"),
        sa.ForeignKeyConstraint(["company_id"], [f"{CONTROL_PLANE_SCHEMA}.companies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["plan_id"], [f"{CONTROL_PLANE_SCHEMA}.plans.id"]),
        schema=CONTROL_PLANE_SCHEMA,
    )
    op.create_index("ix_licenses_id", "licenses", ["id"], unique=False, schema=CONTROL_PLANE_SCHEMA)
    op.create_index("ix_licenses_company", "licenses", ["company_id"], unique=False, schema=CONTROL_PLANE_SCHEMA)
    op.create_index("ix_licenses_key", "licenses", ["license_key"], unique=False, schema=CONTROL_PLANE_SCHEMA)

    op.create_table(
        "company_entitlements",
        sa.Column("company_id", sa.BigInteger(), nullable=False),
        sa.Column("plan_id", sa.String(length=50), nullable=False),
        sa.Column("effective_limits", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("effective_features", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "custom_overrides", postgresql.JSONB(astext_type=sa.Text()), nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("last_issued_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("snapshot_signature", sa.Text(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("company_id"),
        sa.ForeignKeyConstraint(["company_id"], [f"{CONTROL_PLANE_SCHEMA}.companies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["plan_id"], [f"{CONTROL_PLANE_SCHEMA}.plans.id"]),
        schema=CONTROL_PLANE_SCHEMA,
    )

    # ---- Section 3: Project Registry, Stage History & Outcomes ----
    # DRIFT FIX (Quyet dinh 2): KHONG con cot `local_project_snowflake` /
    # constraint `uq_company_project_local` — du thua vi PK trung tam da la
    # chinh no (BigInt Snowflake), khac voi ban UUID cu o deploy/central_vps.
    op.create_table(
        "projects_registry",
        sa.Column("id", sa.BigInteger(), autoincrement=False, nullable=False),
        sa.Column("company_id", sa.BigInteger(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("slug", sa.String(length=100), nullable=True),
        sa.Column("industry", sa.String(length=100), nullable=True),
        sa.Column("category", sa.String(length=100), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="active"),
        sa.Column("current_stage", sa.String(length=50), nullable=False, server_default="S0_EXPLORE"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("last_stage_change_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["company_id"], [f"{CONTROL_PLANE_SCHEMA}.companies.id"], ondelete="CASCADE"),
        schema=CONTROL_PLANE_SCHEMA,
    )
    op.create_index("ix_projects_registry_id", "projects_registry", ["id"], unique=False, schema=CONTROL_PLANE_SCHEMA)
    op.create_index("ix_projects_registry_company", "projects_registry", ["company_id"], unique=False, schema=CONTROL_PLANE_SCHEMA)
    op.create_index("ix_projects_registry_stage", "projects_registry", ["current_stage"], unique=False, schema=CONTROL_PLANE_SCHEMA)

    op.create_table(
        "project_stage_history",
        sa.Column("id", sa.BigInteger(), autoincrement=False, nullable=False),
        sa.Column("project_id", sa.BigInteger(), nullable=False),
        sa.Column("company_id", sa.BigInteger(), nullable=False),
        sa.Column("from_stage", sa.String(length=50), nullable=True),
        sa.Column("to_stage", sa.String(length=50), nullable=False),
        sa.Column("changed_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("duration_seconds", sa.BigInteger(), nullable=True),
        sa.Column("change_source", sa.String(length=50), nullable=True, server_default="local_sync"),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default=sa.text("'{}'::jsonb")),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["project_id"], [f"{CONTROL_PLANE_SCHEMA}.projects_registry.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["company_id"], [f"{CONTROL_PLANE_SCHEMA}.companies.id"], ondelete="CASCADE"),
        schema=CONTROL_PLANE_SCHEMA,
    )
    op.create_index("ix_project_stage_history_id", "project_stage_history", ["id"], unique=False, schema=CONTROL_PLANE_SCHEMA)
    op.create_index("ix_project_stage_history_project", "project_stage_history", ["project_id"], unique=False, schema=CONTROL_PLANE_SCHEMA)
    op.create_index("ix_project_stage_history_company", "project_stage_history", ["company_id"], unique=False, schema=CONTROL_PLANE_SCHEMA)

    op.create_table(
        "project_outcomes",
        sa.Column("project_id", sa.BigInteger(), nullable=False),
        sa.Column("company_id", sa.BigInteger(), nullable=False),
        sa.Column("first_interview_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("first_experiment_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("mvp_launched_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("first_customer_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("first_revenue_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("has_revenue", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("revenue_band", sa.String(length=50), nullable=True, server_default="0"),
        sa.Column("team_size_band", sa.String(length=50), nullable=True, server_default="1-2"),
        sa.Column("outcome_updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("project_id"),
        sa.ForeignKeyConstraint(["project_id"], [f"{CONTROL_PLANE_SCHEMA}.projects_registry.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["company_id"], [f"{CONTROL_PLANE_SCHEMA}.companies.id"], ondelete="CASCADE"),
        schema=CONTROL_PLANE_SCHEMA,
    )

    op.create_table(
        "project_metrics",
        sa.Column("project_id", sa.BigInteger(), nullable=False),
        sa.Column("company_id", sa.BigInteger(), nullable=False),
        sa.Column("customer_interview_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("experiment_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("validated_assumption_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("invalidated_assumption_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("lead_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("customer_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("active_campaign_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("mvp_release_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_metric_sync_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("project_id"),
        sa.ForeignKeyConstraint(["project_id"], [f"{CONTROL_PLANE_SCHEMA}.projects_registry.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["company_id"], [f"{CONTROL_PLANE_SCHEMA}.companies.id"], ondelete="CASCADE"),
        schema=CONTROL_PLANE_SCHEMA,
    )

    # ---- Section 4: Programs, Cohorts & Ecosystem Intelligence ----
    op.create_table(
        "programs",
        sa.Column("id", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("partner_name", sa.String(length=255), nullable=True, server_default="SIHUB"),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
        schema=CONTROL_PLANE_SCHEMA,
    )

    op.create_table(
        "cohorts",
        sa.Column("id", sa.String(length=100), nullable=False),
        sa.Column("program_id", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["program_id"], [f"{CONTROL_PLANE_SCHEMA}.programs.id"], ondelete="CASCADE"),
        schema=CONTROL_PLANE_SCHEMA,
    )

    op.create_table(
        "program_participants",
        sa.Column("id", sa.BigInteger(), autoincrement=False, nullable=False),
        sa.Column("program_id", sa.String(length=50), nullable=False),
        sa.Column("cohort_id", sa.String(length=100), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("company_id", sa.BigInteger(), nullable=False),
        sa.Column("enrolled_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="active"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("cohort_id", "company_id", name="uq_cohort_participant"),
        sa.ForeignKeyConstraint(["program_id"], [f"{CONTROL_PLANE_SCHEMA}.programs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["cohort_id"], [f"{CONTROL_PLANE_SCHEMA}.cohorts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], [f"{CONTROL_PLANE_SCHEMA}.platform_users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["company_id"], [f"{CONTROL_PLANE_SCHEMA}.companies.id"], ondelete="CASCADE"),
        schema=CONTROL_PLANE_SCHEMA,
    )
    op.create_index("ix_program_participants_id", "program_participants", ["id"], unique=False, schema=CONTROL_PLANE_SCHEMA)
    op.create_index("ix_program_participants_cohort", "program_participants", ["cohort_id"], unique=False, schema=CONTROL_PLANE_SCHEMA)
    op.create_index("ix_program_participants_company", "program_participants", ["company_id"], unique=False, schema=CONTROL_PLANE_SCHEMA)

    op.create_table(
        "project_program_links",
        sa.Column("project_id", sa.BigInteger(), nullable=False),
        sa.Column("cohort_id", sa.String(length=100), nullable=False),
        sa.Column("linked_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("project_id", "cohort_id"),
        sa.ForeignKeyConstraint(["project_id"], [f"{CONTROL_PLANE_SCHEMA}.projects_registry.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["cohort_id"], [f"{CONTROL_PLANE_SCHEMA}.cohorts.id"], ondelete="CASCADE"),
        schema=CONTROL_PLANE_SCHEMA,
    )

    # ---- Section 5: Marketing & Public Edge Registry ----
    op.create_table(
        "company_web_apps",
        sa.Column("id", sa.BigInteger(), autoincrement=False, nullable=False),
        sa.Column("company_id", sa.BigInteger(), nullable=False),
        sa.Column("app_type", sa.String(length=50), nullable=False, server_default="marketing"),
        sa.Column("repository_ref", sa.Text(), nullable=True),
        sa.Column("deployment_mode", sa.String(length=50), nullable=False, server_default="cosa_managed"),
        sa.Column("current_version", sa.String(length=50), nullable=True, server_default="v1.0.0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["company_id"], [f"{CONTROL_PLANE_SCHEMA}.companies.id"], ondelete="CASCADE"),
        schema=CONTROL_PLANE_SCHEMA,
    )
    op.create_index("ix_company_web_apps_id", "company_web_apps", ["id"], unique=False, schema=CONTROL_PLANE_SCHEMA)

    op.create_table(
        "domains",
        sa.Column("id", sa.BigInteger(), autoincrement=False, nullable=False),
        sa.Column("company_id", sa.BigInteger(), nullable=False),
        sa.Column("app_id", sa.BigInteger(), nullable=False),
        sa.Column("hostname", sa.String(length=255), nullable=False),
        sa.Column("domain_type", sa.String(length=50), nullable=False, server_default="cosa_subdomain"),
        sa.Column("verification_status", sa.String(length=50), nullable=False, server_default="verified"),
        sa.Column("ssl_status", sa.String(length=50), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("hostname"),
        sa.ForeignKeyConstraint(["company_id"], [f"{CONTROL_PLANE_SCHEMA}.companies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["app_id"], [f"{CONTROL_PLANE_SCHEMA}.company_web_apps.id"], ondelete="CASCADE"),
        schema=CONTROL_PLANE_SCHEMA,
    )
    op.create_index("ix_domains_id", "domains", ["id"], unique=False, schema=CONTROL_PLANE_SCHEMA)
    op.create_index("ix_domains_hostname", "domains", ["hostname"], unique=False, schema=CONTROL_PLANE_SCHEMA)

    op.create_table(
        "form_submissions",
        sa.Column("id", sa.BigInteger(), autoincrement=False, nullable=False),
        sa.Column("company_id", sa.BigInteger(), nullable=False),
        sa.Column("project_id", sa.BigInteger(), nullable=True),
        sa.Column("form_slug", sa.String(length=100), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("source_domain", sa.String(length=255), nullable=True),
        sa.Column("ip_hash", sa.String(length=64), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("sync_status", sa.String(length=50), nullable=False, server_default="pending"),
        sa.Column("synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["company_id"], [f"{CONTROL_PLANE_SCHEMA}.companies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], [f"{CONTROL_PLANE_SCHEMA}.projects_registry.id"]),
        schema=CONTROL_PLANE_SCHEMA,
    )
    op.create_index("ix_form_submissions_id", "form_submissions", ["id"], unique=False, schema=CONTROL_PLANE_SCHEMA)
    op.create_index(
        "ix_form_submissions_company_sync", "form_submissions", ["company_id", "sync_status"],
        unique=False, schema=CONTROL_PLANE_SCHEMA,
    )

    # `deployments`: TEN BANG TRUNG voi app.platform.core.deployment_models
    # .Deployment o Local Business DB (schema public) — nam trong schema
    # `control_plane` rieng chinh la fix cho va cham nay.
    op.create_table(
        "deployments",
        sa.Column("id", sa.BigInteger(), autoincrement=False, nullable=False),
        sa.Column("company_id", sa.BigInteger(), nullable=False),
        sa.Column("app_id", sa.BigInteger(), nullable=False),
        sa.Column("version", sa.String(length=50), nullable=False),
        sa.Column("target_type", sa.String(length=50), nullable=False, server_default="cosa_shared_vps"),
        sa.Column("target_ref", sa.Text(), nullable=True),
        sa.Column("hostname", sa.String(length=255), nullable=True),
        sa.Column("build_status", sa.String(length=50), nullable=False, server_default="pending"),
        sa.Column("deployment_status", sa.String(length=50), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("deployed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["company_id"], [f"{CONTROL_PLANE_SCHEMA}.companies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["app_id"], [f"{CONTROL_PLANE_SCHEMA}.company_web_apps.id"], ondelete="CASCADE"),
        schema=CONTROL_PLANE_SCHEMA,
    )
    op.create_index("ix_deployments_id", "deployments", ["id"], unique=False, schema=CONTROL_PLANE_SCHEMA)

    # ---- Section 6: Session & Refresh Token Management ----
    # Bang nay CHI co o infra/supabase/migrations/... — bi thieu (drift do bo
    # sot) o deploy/central_vps/init_central_postgres.sql. Mang nguyen sang.
    op.create_table(
        "user_sessions",
        sa.Column("id", sa.BigInteger(), autoincrement=False, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("refresh_token_hash", sa.Text(), nullable=False),
        sa.Column("device_info", postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default=sa.text("'{}'::jsonb")),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], [f"{CONTROL_PLANE_SCHEMA}.platform_users.id"], ondelete="CASCADE"),
        schema=CONTROL_PLANE_SCHEMA,
    )
    op.create_index("ix_user_sessions_id", "user_sessions", ["id"], unique=False, schema=CONTROL_PLANE_SCHEMA)
    op.create_index("ix_user_sessions_user", "user_sessions", ["user_id"], unique=False, schema=CONTROL_PLANE_SCHEMA)
    op.create_index("ix_user_sessions_token", "user_sessions", ["refresh_token_hash"], unique=False, schema=CONTROL_PLANE_SCHEMA)

    # ---- Seed data (mac dinh: free/starter/pro/enterprise + 2 chuong trinh) ----
    op.execute(
        sa.text(
            """
            INSERT INTO control_plane.plans (id, name, description, default_limits, default_features, is_public)
            VALUES
                ('free', 'Free / Learning', 'Danh cho hoc vien, nguoi moi bat dau va chuong trinh vuon uom khoi nghiep',
                 '{"max_projects": 1, "max_seats": 2, "max_scheduled_agents": 1}'::jsonb,
                 '{"marketing": true, "crm": true, "finance": false, "custom_domain": false}'::jsonb, true),
                ('starter', 'Starter', 'Danh cho cac du an khoi nghiep don le dang giai doan kiem chung thi truong',
                 '{"max_projects": 3, "max_seats": 5, "max_scheduled_agents": 3}'::jsonb,
                 '{"marketing": true, "crm": true, "finance": true, "custom_domain": true}'::jsonb, true),
                ('pro', 'Pro / Scale', 'Danh cho doanh nghiep tang truong can tu dong hoa toan dien',
                 '{"max_projects": 20, "max_seats": 20, "max_scheduled_agents": 10}'::jsonb,
                 '{"marketing": true, "crm": true, "finance": true, "custom_domain": true, "priority_sync": true}'::jsonb, true),
                ('enterprise', 'Enterprise Private', 'Danh cho doanh nghiep lon voi ha tang server rieng biet',
                 '{"max_projects": 999, "max_seats": 999, "max_scheduled_agents": 999}'::jsonb,
                 '{"marketing": true, "crm": true, "finance": true, "custom_domain": true, "private_intake": true}'::jsonb, false)
            ON CONFLICT (id) DO NOTHING
            """
        )
    )
    op.execute(
        sa.text(
            """
            INSERT INTO control_plane.programs (id, name, partner_name, description)
            VALUES
                ('sihub_incubation', 'Chuong trinh Uom tao SIHUB Startup', 'SIHUB', 'Chuong trinh tang toc khoi nghiep doi moi sang tao ho tro boi SIHUB'),
                ('cosa_founder_fellowship', 'COSA Founder Fellowship 2026', 'COSA', 'Chuong trinh dong hanh xay dung doanh nghiep cung tro ly ao AI')
            ON CONFLICT (id) DO NOTHING
            """
        )
    )


def downgrade() -> None:
    op.execute("DELETE FROM control_plane.programs WHERE id IN ('sihub_incubation', 'cosa_founder_fellowship')")
    op.execute("DELETE FROM control_plane.plans WHERE id IN ('free', 'starter', 'pro', 'enterprise')")

    op.drop_index("ix_user_sessions_token", table_name="user_sessions", schema=CONTROL_PLANE_SCHEMA)
    op.drop_index("ix_user_sessions_user", table_name="user_sessions", schema=CONTROL_PLANE_SCHEMA)
    op.drop_index("ix_user_sessions_id", table_name="user_sessions", schema=CONTROL_PLANE_SCHEMA)
    op.drop_table("user_sessions", schema=CONTROL_PLANE_SCHEMA)

    op.drop_index("ix_deployments_id", table_name="deployments", schema=CONTROL_PLANE_SCHEMA)
    op.drop_table("deployments", schema=CONTROL_PLANE_SCHEMA)

    op.drop_index("ix_form_submissions_company_sync", table_name="form_submissions", schema=CONTROL_PLANE_SCHEMA)
    op.drop_index("ix_form_submissions_id", table_name="form_submissions", schema=CONTROL_PLANE_SCHEMA)
    op.drop_table("form_submissions", schema=CONTROL_PLANE_SCHEMA)

    op.drop_index("ix_domains_hostname", table_name="domains", schema=CONTROL_PLANE_SCHEMA)
    op.drop_index("ix_domains_id", table_name="domains", schema=CONTROL_PLANE_SCHEMA)
    op.drop_table("domains", schema=CONTROL_PLANE_SCHEMA)

    op.drop_index("ix_company_web_apps_id", table_name="company_web_apps", schema=CONTROL_PLANE_SCHEMA)
    op.drop_table("company_web_apps", schema=CONTROL_PLANE_SCHEMA)

    op.drop_table("project_program_links", schema=CONTROL_PLANE_SCHEMA)

    op.drop_index("ix_program_participants_company", table_name="program_participants", schema=CONTROL_PLANE_SCHEMA)
    op.drop_index("ix_program_participants_cohort", table_name="program_participants", schema=CONTROL_PLANE_SCHEMA)
    op.drop_index("ix_program_participants_id", table_name="program_participants", schema=CONTROL_PLANE_SCHEMA)
    op.drop_table("program_participants", schema=CONTROL_PLANE_SCHEMA)

    op.drop_table("cohorts", schema=CONTROL_PLANE_SCHEMA)
    op.drop_table("programs", schema=CONTROL_PLANE_SCHEMA)

    op.drop_table("project_metrics", schema=CONTROL_PLANE_SCHEMA)
    op.drop_table("project_outcomes", schema=CONTROL_PLANE_SCHEMA)

    op.drop_index("ix_project_stage_history_company", table_name="project_stage_history", schema=CONTROL_PLANE_SCHEMA)
    op.drop_index("ix_project_stage_history_project", table_name="project_stage_history", schema=CONTROL_PLANE_SCHEMA)
    op.drop_index("ix_project_stage_history_id", table_name="project_stage_history", schema=CONTROL_PLANE_SCHEMA)
    op.drop_table("project_stage_history", schema=CONTROL_PLANE_SCHEMA)

    op.drop_index("ix_projects_registry_stage", table_name="projects_registry", schema=CONTROL_PLANE_SCHEMA)
    op.drop_index("ix_projects_registry_company", table_name="projects_registry", schema=CONTROL_PLANE_SCHEMA)
    op.drop_index("ix_projects_registry_id", table_name="projects_registry", schema=CONTROL_PLANE_SCHEMA)
    op.drop_table("projects_registry", schema=CONTROL_PLANE_SCHEMA)

    op.drop_table("company_entitlements", schema=CONTROL_PLANE_SCHEMA)

    op.drop_index("ix_licenses_key", table_name="licenses", schema=CONTROL_PLANE_SCHEMA)
    op.drop_index("ix_licenses_company", table_name="licenses", schema=CONTROL_PLANE_SCHEMA)
    op.drop_index("ix_licenses_id", table_name="licenses", schema=CONTROL_PLANE_SCHEMA)
    op.drop_table("licenses", schema=CONTROL_PLANE_SCHEMA)

    op.drop_table("plans", schema=CONTROL_PLANE_SCHEMA)

    op.drop_index("ix_company_memberships_company", table_name="company_memberships", schema=CONTROL_PLANE_SCHEMA)
    op.drop_index("ix_company_memberships_user", table_name="company_memberships", schema=CONTROL_PLANE_SCHEMA)
    op.drop_index("ix_company_memberships_id", table_name="company_memberships", schema=CONTROL_PLANE_SCHEMA)
    op.drop_table("company_memberships", schema=CONTROL_PLANE_SCHEMA)

    op.drop_index("ix_companies_status", table_name="companies", schema=CONTROL_PLANE_SCHEMA)
    op.drop_index("ix_companies_slug", table_name="companies", schema=CONTROL_PLANE_SCHEMA)
    op.drop_index("ix_companies_id", table_name="companies", schema=CONTROL_PLANE_SCHEMA)
    op.drop_table("companies", schema=CONTROL_PLANE_SCHEMA)

    op.drop_index("ix_platform_users_status", table_name="platform_users", schema=CONTROL_PLANE_SCHEMA)
    op.drop_index("ix_platform_users_phone", table_name="platform_users", schema=CONTROL_PLANE_SCHEMA)
    op.drop_index("ix_platform_users_email", table_name="platform_users", schema=CONTROL_PLANE_SCHEMA)
    op.drop_index("ix_platform_users_id", table_name="platform_users", schema=CONTROL_PLANE_SCHEMA)
    op.drop_table("platform_users", schema=CONTROL_PLANE_SCHEMA)

    op.execute(f"DROP SCHEMA IF EXISTS {CONTROL_PLANE_SCHEMA} CASCADE")






