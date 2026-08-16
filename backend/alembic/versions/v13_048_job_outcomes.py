"""Create job_outcomes table.

Revision ID: v13_048_job_outcomes
Revises: v13_047_job_skill_runtime
Create Date: 2026-08-16 00:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "v13_048_job_outcomes"
down_revision: Union[str, Sequence[str], None] = "v13_047_job_skill_runtime"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    if "job_outcomes" not in tables:
        op.create_table(
            "job_outcomes",
            sa.Column("id", sa.BigInteger(), nullable=False, primary_key=True),
            sa.Column("workspace_id", sa.BigInteger(), sa.ForeignKey("workspaces.id"), nullable=False),
            sa.Column("run_id", sa.BigInteger(), sa.ForeignKey("agent_runs.id"), nullable=False),
            sa.Column("metric", sa.String(length=100), nullable=False),
            sa.Column("expected_jsonb", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
            sa.Column("actual_jsonb", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
            sa.Column("verified", sa.Boolean(), nullable=False, server_default="false"),
            sa.Column("source_ref", sa.String(length=255), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        )
        op.create_index("ix_job_outcomes_workspace_id", "job_outcomes", ["workspace_id"])
        op.create_index("ix_job_outcomes_run_id", "job_outcomes", ["run_id"])


def downgrade() -> None:
    op.drop_table("job_outcomes")
