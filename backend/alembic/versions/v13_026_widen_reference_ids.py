"""widen unconstrained entity references for Snowflake IDs

Revision ID: v13_026_reference_ids
Revises: v13_025_knowledge_actor
"""

from alembic import op
import sqlalchemy as sa


revision = "v13_026_reference_ids"
down_revision = "v13_025_knowledge_actor"
branch_labels = None
depends_on = None


_REFERENCES = (
    ("context_pack_sources", "revision_id"),
    ("pestel_items", "portfolio_id"),
    ("projects", "portfolio_id"),
    ("strategic_decisions", "rationale_revision_id"),
    ("strategy_analyses", "portfolio_id"),
    ("strategy_analyses", "output_revision_id"),
    ("swot_items", "portfolio_id"),
    ("tows_options", "portfolio_id"),
    ("workflow_definitions", "current_version_id"),
)


def upgrade() -> None:
    for table_name, column_name in _REFERENCES:
        op.alter_column(
            table_name,
            column_name,
            existing_type=sa.Integer(),
            type_=sa.BigInteger(),
            existing_nullable=True,
            postgresql_using=f"{column_name}::bigint",
        )


def downgrade() -> None:
    raise RuntimeError("Cannot downgrade Snowflake reference columns without data loss")
