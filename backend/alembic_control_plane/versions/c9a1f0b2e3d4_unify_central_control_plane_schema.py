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


def downgrade() -> None:
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
