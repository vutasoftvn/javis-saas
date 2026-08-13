"""add dependency DAG fields to task_dependencies

Revision ID: v13_008_dag
Revises: v13_007_contracts
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "v13_008_dag"
down_revision: Union[str, Sequence[str], None] = "v13_007_contracts"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("task_dependencies", sa.Column("dependency_type", sa.String(50), nullable=True))
    op.add_column("task_dependencies", sa.Column("status", sa.String(50), server_default="PENDING", nullable=False))


def downgrade() -> None:
    op.drop_column("task_dependencies", "status")
    op.drop_column("task_dependencies", "dependency_type")
