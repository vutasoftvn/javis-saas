"""create V13 Legal and Sales function tables

Revision ID: v13_004_functions
Revises: v13_003_lessons
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "v13_004_functions"
down_revision: Union[str, Sequence[str], None] = "v13_003_lessons"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "legal_checklist_items",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("workspace_id", sa.BigInteger(), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("evidence_artifact_id", sa.BigInteger(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"]),
        sa.ForeignKeyConstraint(["evidence_artifact_id"], ["artifacts.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_legal_checklist_items_workspace_id", "legal_checklist_items", ["workspace_id"])
    op.create_table(
        "legal_obligations",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("workspace_id", sa.BigInteger(), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("due_at", sa.DateTime(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_legal_obligations_workspace_id", "legal_obligations", ["workspace_id"])
    op.create_table(
        "sales_leads",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("workspace_id", sa.BigInteger(), nullable=False),
        sa.Column("key_result_id", sa.BigInteger(), nullable=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("company", sa.String(255), nullable=True),
        sa.Column("stage", sa.String(30), nullable=False),
        sa.Column("value", sa.Float(), nullable=True),
        sa.Column("owner_id", sa.BigInteger(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"]),
        sa.ForeignKeyConstraint(["key_result_id"], ["key_results.id"]),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_sales_leads_workspace_id", "sales_leads", ["workspace_id"])
    op.create_index("ix_sales_leads_key_result_id", "sales_leads", ["key_result_id"])


def downgrade() -> None:
    op.drop_table("sales_leads")
    op.drop_table("legal_obligations")
    op.drop_table("legal_checklist_items")
