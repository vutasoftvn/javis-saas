"""Create protected_resources and protected_resource_revisions tables.

Revision ID: v13_046_protected_resources
Revises: v13_045_tool_obs_cols
Create Date: 2026-08-16 00:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "v13_046_protected_resources"
down_revision: Union[str, Sequence[str], None] = "v13_045_tool_obs_cols"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    if "protected_resources" not in tables:
        op.create_table(
            "protected_resources",
            sa.Column("id", sa.BigInteger(), nullable=False, primary_key=True),
            sa.Column("workspace_id", sa.BigInteger(), sa.ForeignKey("workspaces.id"), nullable=False),
            sa.Column("resource_type", sa.String(length=50), nullable=False),
            sa.Column("resource_key", sa.String(length=255), nullable=False),
            sa.Column("active_revision_no", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("editable_by", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='["admin"]'),
            sa.Column("resettable", sa.Boolean(), nullable=False, server_default="true"),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.UniqueConstraint("workspace_id", "resource_type", "resource_key", name="uix_protected_resources_ws_type_key"),
        )
        op.create_index("ix_protected_resources_workspace_id", "protected_resources", ["workspace_id"])
        op.create_index("ix_protected_resources_resource_type", "protected_resources", ["resource_type"])
        op.create_index("ix_protected_resources_resource_key", "protected_resources", ["resource_key"])

    if "protected_resource_revisions" not in tables:
        op.create_table(
            "protected_resource_revisions",
            sa.Column("id", sa.BigInteger(), nullable=False, primary_key=True),
            sa.Column("resource_id", sa.BigInteger(), sa.ForeignKey("protected_resources.id"), nullable=False),
            sa.Column("revision_no", sa.Integer(), nullable=False),
            sa.Column("content_jsonb", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
            sa.Column("is_default", sa.Boolean(), nullable=False, server_default="false"),
            sa.Column("status", sa.String(length=24), nullable=False, server_default="ACTIVE"),
            sa.Column("created_by", sa.BigInteger(), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("checksum", sa.String(length=128), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.UniqueConstraint("resource_id", "revision_no", name="uix_protected_resource_revisions_res_rev"),
        )
        op.create_index("ix_protected_resource_revisions_resource_id", "protected_resource_revisions", ["resource_id"])


def downgrade() -> None:
    op.drop_table("protected_resource_revisions")
    op.drop_table("protected_resources")
