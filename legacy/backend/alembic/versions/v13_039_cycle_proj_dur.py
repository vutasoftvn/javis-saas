"""Add project_id and duration_weeks to twelve_week_cycles.

Revision ID: v13_039_cycle_proj_dur
Revises: v13_038_report_automation_tables
Create Date: 2026-08-15 00:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = "v13_039_cycle_proj_dur"
down_revision: Union[str, Sequence[str], None] = "v13_038_report_automation_tables"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [c["name"] for c in inspector.get_columns("twelve_week_cycles")]

    if "project_id" not in columns:
        op.add_column(
            "twelve_week_cycles",
            sa.Column("project_id", sa.BigInteger(), sa.ForeignKey("projects.id"), nullable=True),
        )
        op.create_index(
            "ix_twelve_week_cycle_project_id",
            "twelve_week_cycles",
            ["project_id"],
            unique=False,
        )

    if "duration_weeks" not in columns:
        op.add_column(
            "twelve_week_cycles",
            sa.Column("duration_weeks", sa.Integer(), nullable=False, server_default="13"),
        )


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [c["name"] for c in inspector.get_columns("twelve_week_cycles")]

    if "duration_weeks" in columns:
        op.drop_column("twelve_week_cycles", "duration_weeks")

    if "project_id" in columns:
        op.drop_index("ix_twelve_week_cycle_project_id", table_name="twelve_week_cycles")
        op.drop_column("twelve_week_cycles", "project_id")
