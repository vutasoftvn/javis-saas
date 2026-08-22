"""add runtime contracts and work reviews

Revision ID: v13_007_contracts
Revises: v13_006_defaults
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "v13_007_contracts"
down_revision: Union[str, Sequence[str], None] = "v13_006_defaults"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add outcomes fields
    op.add_column("outcomes", sa.Column("task_id", sa.BigInteger(), nullable=True))
    op.create_foreign_key("fk_outcomes_task_id", "outcomes", "tasks", ["task_id"], ["id"])
    op.create_index("ix_outcomes_task_id", "outcomes", ["task_id"])

    op.add_column("outcomes", sa.Column("required_artifacts", postgresql.JSONB(), nullable=True))
    op.add_column("outcomes", sa.Column("reviewer_id", sa.BigInteger(), nullable=True))
    op.create_foreign_key("fk_outcomes_reviewer_id", "outcomes", "users", ["reviewer_id"], ["id"])
    op.create_index("ix_outcomes_reviewer_id", "outcomes", ["reviewer_id"])

    op.add_column("outcomes", sa.Column("review_type", sa.String(50), nullable=True))
    op.add_column("outcomes", sa.Column("validation_rules", postgresql.JSONB(), nullable=True))
    op.add_column("outcomes", sa.Column("rework_count", sa.BigInteger(), server_default="0", nullable=False))

    # Create work_reviews table
    op.create_table(
        "work_reviews",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=False),
        sa.Column("workspace_id", sa.BigInteger(), sa.ForeignKey("workspaces.id"), nullable=False, index=True),
        sa.Column("outcome_id", sa.BigInteger(), sa.ForeignKey("outcomes.id"), nullable=False, index=True),
        sa.Column("reviewer_type", sa.String(50), nullable=False),
        sa.Column("reviewer_id", sa.BigInteger(), sa.ForeignKey("users.id"), nullable=True, index=True),
        sa.Column("result", sa.String(50), nullable=False),
        sa.Column("feedback", sa.Text(), nullable=True),
        sa.Column("evidence_refs", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )


def downgrade() -> None:
    op.drop_table("work_reviews")
    op.drop_column("outcomes", "rework_count")
    op.drop_column("outcomes", "validation_rules")
    op.drop_column("outcomes", "review_type")
    op.drop_index("ix_outcomes_reviewer_id", table_name="outcomes")
    op.drop_constraint("fk_outcomes_reviewer_id", "outcomes", type_="foreignkey")
    op.drop_column("outcomes", "reviewer_id")
    op.drop_column("outcomes", "required_artifacts")
    op.drop_index("ix_outcomes_task_id", table_name="outcomes")
    op.drop_constraint("fk_outcomes_task_id", "outcomes", type_="foreignkey")
    op.drop_column("outcomes", "task_id")
