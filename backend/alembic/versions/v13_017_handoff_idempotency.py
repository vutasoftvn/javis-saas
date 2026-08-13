"""add idempotency key to structured handoffs

Revision ID: v13_017_handoff_idempotency
Revises: v13_016_sales_crm_flag_defaults
"""
from alembic import op
import sqlalchemy as sa


revision = "v13_017_handoff_idempotency"
down_revision = "v13_016_sales_crm_flag_defaults"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("handoffs", sa.Column("idempotency_key", sa.String(length=255), nullable=True))
    op.create_unique_constraint(
        "uq_handoffs_workspace_idempotency_key",
        "handoffs",
        ["workspace_id", "idempotency_key"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_handoffs_workspace_idempotency_key", "handoffs", type_="unique")
    op.drop_column("handoffs", "idempotency_key")
