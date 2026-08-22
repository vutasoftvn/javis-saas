"""create cross-function lessons

Revision ID: v13_003_lessons
Revises: v13_002_okr_work
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "v13_003_lessons"
down_revision: Union[str, Sequence[str], None] = "v13_002_okr_work"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "lessons",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("workspace_id", sa.BigInteger(), nullable=False),
        sa.Column("cycle_id", sa.BigInteger(), nullable=True),
        sa.Column("week_no", sa.Integer(), nullable=True),
        sa.Column("function", sa.String(20), nullable=True),
        sa.Column("project_id", sa.BigInteger(), nullable=True),
        sa.Column("observation", sa.Text(), nullable=False),
        sa.Column("evidence_refs", postgresql.JSONB(), nullable=True),
        sa.Column("interpretation", sa.Text(), nullable=True),
        sa.Column("recommendation", sa.Text(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("created_by", sa.BigInteger(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"]),
        sa.ForeignKeyConstraint(["cycle_id"], ["twelve_week_cycles.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in ("workspace_id", "cycle_id", "function", "project_id"):
        op.create_index(f"ix_lessons_{column}", "lessons", [column])


def downgrade() -> None:
    op.drop_table("lessons")
