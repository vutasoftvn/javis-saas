"""Create capability_grants table for Capability Gateway.

Revision ID: v13_043_capability_grants
Revises: v13_042_step_retry_cols
Create Date: 2026-08-15 00:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "v13_043_capability_grants"
down_revision: Union[str, Sequence[str], None] = "v13_042_step_retry_cols"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    if "capability_grants" not in tables:
        op.create_table(
            "capability_grants",
            sa.Column("id", sa.BigInteger(), nullable=False, primary_key=True),
            sa.Column("workspace_id", sa.BigInteger(), sa.ForeignKey("workspaces.id"), nullable=False, index=True),
            sa.Column("company_id", sa.BigInteger(), nullable=True, index=True),
            sa.Column("subject_type", sa.String(50), nullable=False, server_default="agent"),
            sa.Column("subject_id", sa.String(100), nullable=False, index=True),
            sa.Column("capability", sa.String(150), nullable=False, index=True),
            sa.Column("resource_type", sa.String(100), nullable=True),
            sa.Column("resource_id", sa.String(255), nullable=True),
            sa.Column("scope_jsonb", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column("granted_by", sa.BigInteger(), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("notes", sa.Text(), nullable=True),
        )
        op.create_index(
            "ix_capability_grants_ws_subj_cap",
            "capability_grants",
            ["workspace_id", "subject_type", "subject_id", "capability"],
        )


def downgrade() -> None:
    op.drop_index("ix_capability_grants_ws_subj_cap", table_name="capability_grants")
    op.drop_table("capability_grants")
