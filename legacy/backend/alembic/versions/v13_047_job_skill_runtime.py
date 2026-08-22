"""Add job_type and project_id to agent_runs, and skills_jsonb to agent_plans.

Revision ID: v13_047_job_skill_runtime
Revises: v13_046_protected_resources
Create Date: 2026-08-16 00:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "v13_047_job_skill_runtime"
down_revision: Union[str, Sequence[str], None] = "v13_046_protected_resources"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    # 1. agent_runs columns
    run_cols = [c["name"] for c in inspector.get_columns("agent_runs")]
    if "job_type" not in run_cols:
        op.add_column("agent_runs", sa.Column("job_type", sa.String(length=100), nullable=True))
        op.create_index("ix_agent_runs_job_type", "agent_runs", ["job_type"])
    if "project_id" not in run_cols:
        op.add_column("agent_runs", sa.Column("project_id", sa.BigInteger(), nullable=True))
        op.create_index("ix_agent_runs_project_id", "agent_runs", ["project_id"])

    # 2. agent_plans columns
    plan_cols = [c["name"] for c in inspector.get_columns("agent_plans")]
    if "skills_jsonb" not in plan_cols:
        op.add_column("agent_plans", sa.Column("skills_jsonb", postgresql.JSONB(astext_type=sa.Text()), nullable=True))


def downgrade() -> None:
    op.drop_column("agent_plans", "skills_jsonb")
    op.drop_index("ix_agent_runs_project_id", table_name="agent_runs")
    op.drop_index("ix_agent_runs_job_type", table_name="agent_runs")
    op.drop_column("agent_runs", "project_id")
    op.drop_column("agent_runs", "job_type")
