"""link sales opportunities to 12-week cycles

Revision ID: v13_018_sales_opportunity_cycle
Revises: v13_017_handoff_idempotency
"""
from alembic import op
import sqlalchemy as sa

revision = "v13_018_sales_opportunity_cycle"
down_revision = "v13_017_handoff_idempotency"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("sales_opportunities", sa.Column("cycle_id", sa.BigInteger(), nullable=True))
    op.create_foreign_key("fk_sales_opportunities_cycle_id", "sales_opportunities", "twelve_week_cycles", ["cycle_id"], ["id"])
    op.create_index("ix_sales_opportunities_cycle_id", "sales_opportunities", ["cycle_id"])


def downgrade() -> None:
    op.drop_index("ix_sales_opportunities_cycle_id", table_name="sales_opportunities")
    op.drop_constraint("fk_sales_opportunities_cycle_id", "sales_opportunities", type_="foreignkey")
    op.drop_column("sales_opportunities", "cycle_id")
