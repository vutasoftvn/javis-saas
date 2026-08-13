"""enforce one chunk per revision ordinal

Revision ID: v13_019_document_chunk_uniqueness
Revises: v13_018_sales_opportunity_cycle
"""
from alembic import op

revision = "v13_019_document_chunk_uniqueness"
down_revision = "v13_018_sales_opportunity_cycle"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Keep the earliest row for each ordinal so historical retry duplicates do
    # not prevent the new data-integrity constraint from being installed.
    op.execute("""
        DELETE FROM document_chunks AS duplicate
        USING document_chunks AS canonical
        WHERE duplicate.revision_id = canonical.revision_id
          AND duplicate.ordinal = canonical.ordinal
          AND duplicate.id > canonical.id
    """)
    op.create_unique_constraint(
        "uq_document_chunks_revision_ordinal",
        "document_chunks",
        ["revision_id", "ordinal"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_document_chunks_revision_ordinal", "document_chunks", type_="unique")
