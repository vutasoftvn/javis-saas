"""Add start_date and end_date to projects, and end_date to weekly_plans.

Revision ID: v13_049_project_weekly_dates
Revises: v13_048_job_outcomes
Create Date: 2026-08-16 00:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = "v13_049_project_weekly_dates"
down_revision: Union[str, Sequence[str], None] = "v13_048_job_outcomes"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    # projects table columns
    project_cols = [c["name"] for c in inspector.get_columns("projects")]
    if "start_date" not in project_cols:
        op.add_column("projects", sa.Column("start_date", sa.DateTime(), nullable=True))
    if "end_date" not in project_cols:
        op.add_column("projects", sa.Column("end_date", sa.DateTime(), nullable=True))

    # weekly_plans table columns
    weekly_cols = [c["name"] for c in inspector.get_columns("weekly_plans")]
    if "end_date" not in weekly_cols:
        op.add_column("weekly_plans", sa.Column("end_date", sa.DateTime(), nullable=True))


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    weekly_cols = [c["name"] for c in inspector.get_columns("weekly_plans")]
    if "end_date" in weekly_cols:
        op.drop_column("weekly_plans", "end_date")

    project_cols = [c["name"] for c in inspector.get_columns("projects")]
    if "end_date" in project_cols:
        op.drop_column("projects", "end_date")
    if "start_date" in project_cols:
        op.drop_column("projects", "start_date")
