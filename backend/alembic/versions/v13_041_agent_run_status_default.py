"""Alter default status on agent_runs to created.

Revision ID: v13_041_agent_run_status_default
Revises: v13_040_agent_events_columns
Create Date: 2026-08-15 00:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = "v13_041_agent_run_status_default"
down_revision: Union[str, Sequence[str], None] = "v13_040_agent_events_columns"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "agent_runs",
        "status",
        existing_type=sa.String(length=50),
        server_default="created",
        nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "agent_runs",
        "status",
        existing_type=sa.String(length=50),
        server_default="completed",
        nullable=False,
    )
