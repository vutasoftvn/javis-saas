"""widen knowledge provenance identifiers for Snowflake IDs

Revision ID: v13_025_knowledge_actor
Revises: v13_024_functional_flags
"""

from alembic import op
import sqlalchemy as sa


revision = "v13_025_knowledge_actor"
down_revision = "v13_024_functional_flags"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "knowledge_objects",
        "generated_by",
        existing_type=sa.Integer(),
        type_=sa.BigInteger(),
        existing_nullable=True,
        postgresql_using="generated_by::bigint",
    )


def downgrade() -> None:
    # A Snowflake value cannot safely be represented by INTEGER. Refuse a
    # lossy downgrade rather than corrupting provenance data.
    raise RuntimeError("Cannot downgrade knowledge_objects.generated_by without data loss")
