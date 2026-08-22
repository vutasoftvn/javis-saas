"""Add COSA Hybrid Data Architecture Platform baseline fields (Phase 1).

Adds platform_user_id to users.
Adds platform_company_id to workspaces.
Adds platform_project_id, sync_status, and last_synced_at to projects.

Revision ID: v13_052_hybrid_platform_baseline
Revises: v13_051_cosa_cofounder_schema
Create Date: 2026-08-19 08:30:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = "v13_052_hybrid_platform_baseline"
down_revision: Union[str, Sequence[str], None] = "v13_051_cosa_cofounder_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    # 1. Update users table with platform_user_id
    if "users" in tables:
        columns = [c["name"] for c in inspector.get_columns("users")]
        if "platform_user_id" not in columns:
            op.add_column(
                "users",
                sa.Column("platform_user_id", sa.String(length=36), nullable=True),
            )
            op.create_index("ix_users_platform_user_id", "users", ["platform_user_id"], unique=True)

    # 2. Update workspaces table with platform_company_id
    if "workspaces" in tables:
        columns = [c["name"] for c in inspector.get_columns("workspaces")]
        if "platform_company_id" not in columns:
            op.add_column(
                "workspaces",
                sa.Column("platform_company_id", sa.String(length=36), nullable=True),
            )
            op.create_index("ix_workspaces_platform_company_id", "workspaces", ["platform_company_id"], unique=True)

    # 3. Update projects table with platform_project_id, sync_status, and last_synced_at
    if "projects" in tables:
        columns = [c["name"] for c in inspector.get_columns("projects")]
        if "platform_project_id" not in columns:
            op.add_column(
                "projects",
                sa.Column("platform_project_id", sa.String(length=36), nullable=True),
            )
            op.create_index("ix_projects_platform_project_id", "projects", ["platform_project_id"], unique=True)

        if "sync_status" not in columns:
            op.add_column(
                "projects",
                sa.Column("sync_status", sa.String(length=50), nullable=False, server_default="synced"),
            )
            op.create_index("ix_projects_sync_status", "projects", ["sync_status"])

        if "last_synced_at" not in columns:
            op.add_column(
                "projects",
                sa.Column("last_synced_at", sa.DateTime(), nullable=True),
            )


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    if "projects" in tables:
        columns = [c["name"] for c in inspector.get_columns("projects")]
        if "last_synced_at" in columns:
            op.drop_column("projects", "last_synced_at")
        if "sync_status" in columns:
            op.drop_index("ix_projects_sync_status", table_name="projects")
            op.drop_column("projects", "sync_status")
        if "platform_project_id" in columns:
            op.drop_index("ix_projects_platform_project_id", table_name="projects")
            op.drop_column("projects", "platform_project_id")

    if "workspaces" in tables:
        columns = [c["name"] for c in inspector.get_columns("workspaces")]
        if "platform_company_id" in columns:
            op.drop_index("ix_workspaces_platform_company_id", table_name="workspaces")
            op.drop_column("workspaces", "platform_company_id")

    if "users" in tables:
        columns = [c["name"] for c in inspector.get_columns("users")]
        if "platform_user_id" in columns:
            op.drop_index("ix_users_platform_user_id", table_name="users")
            op.drop_column("users", "platform_user_id")
