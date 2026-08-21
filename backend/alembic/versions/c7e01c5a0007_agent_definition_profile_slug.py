"""add agent_definitions.profile_slug

Revision ID: c7e01c5a0007
Revises: c6e01c5a0006
Create Date: 2026-08-21 10:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "c7e01c5a0007"
down_revision: Union[str, Sequence[str], None] = "c6e01c5a0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "agent_definitions",
        sa.Column("profile_slug", sa.String(length=100), nullable=True),
    )
    op.create_index(
        "ix_agent_definitions_profile_slug",
        "agent_definitions",
        ["profile_slug"],
    )


def downgrade() -> None:
    op.drop_index("ix_agent_definitions_profile_slug", table_name="agent_definitions")
    op.drop_column("agent_definitions", "profile_slug")
