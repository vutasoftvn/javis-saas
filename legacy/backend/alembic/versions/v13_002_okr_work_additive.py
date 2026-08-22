"""add V13 traceability fields

Revision ID: v13_002_okr_work
Revises: v13_001_flags
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "v13_002_okr_work"
down_revision: Union[str, Sequence[str], None] = "v13_001_flags"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("tasks", sa.Column("function", sa.String(20), nullable=True))
    op.create_index("ix_tasks_function", "tasks", ["function"])
    op.add_column("outcomes", sa.Column("function", sa.String(20), nullable=True))
    op.add_column("outcomes", sa.Column("cycle_id", sa.BigInteger(), nullable=True))
    op.create_foreign_key("fk_outcomes_cycle_id", "outcomes", "twelve_week_cycles", ["cycle_id"], ["id"])
    op.create_index("ix_outcomes_function", "outcomes", ["function"])
    op.create_index("ix_outcomes_cycle_id", "outcomes", ["cycle_id"])
    op.add_column("okr_objectives", sa.Column("why", sa.Text(), nullable=True))
    op.add_column("key_results", sa.Column("metric_type", sa.String(50), nullable=True))
    op.add_column("key_results", sa.Column("evidence_refs", postgresql.JSONB(), nullable=True))


def downgrade() -> None:
    op.drop_column("key_results", "evidence_refs")
    op.drop_column("key_results", "metric_type")
    op.drop_column("okr_objectives", "why")
    op.drop_index("ix_outcomes_cycle_id", table_name="outcomes")
    op.drop_index("ix_outcomes_function", table_name="outcomes")
    op.drop_constraint("fk_outcomes_cycle_id", "outcomes", type_="foreignkey")
    op.drop_column("outcomes", "cycle_id")
    op.drop_column("outcomes", "function")
    op.drop_index("ix_tasks_function", table_name="tasks")
    op.drop_column("tasks", "function")
