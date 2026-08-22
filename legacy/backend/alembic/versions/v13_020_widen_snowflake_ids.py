"""widen mis-typed snowflake ID reference columns to bigint

Revision ID: v13_020_widen_snowflake_ids
Revises: v13_019_doc_chunk_uniqueness

audit_logs.actor_id/target_id, task_workflow_bindings.workflow_version_id,
workflow_runs.version_id and okr_links.from_entity_id/to_entity_id were declared
as bare `Mapped[int]` (SQLAlchemy's default int4) instead of BigInteger, even
though every value they hold is a 64-bit Snowflake ID from
app.core.snowflake.generate_snowflake_id. Any insert with a real snowflake
value overflows int4 ("integer out of range") - e.g. every StrategyCanvas
create/update audit log entry.
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "v13_020_widen_snowflake_ids"
down_revision: Union[str, Sequence[str], None] = "v13_019_doc_chunk_uniqueness"
branch_labels = None
depends_on = None

_COLUMNS = (
    ("audit_logs", "actor_id"),
    ("audit_logs", "target_id"),
    ("task_workflow_bindings", "workflow_version_id"),
    ("workflow_runs", "version_id"),
    ("okr_links", "from_entity_id"),
    ("okr_links", "to_entity_id"),
)


def upgrade() -> None:
    for table, column in _COLUMNS:
        op.alter_column(table, column, existing_type=sa.Integer(), type_=sa.BigInteger())


def downgrade() -> None:
    for table, column in reversed(_COLUMNS):
        op.alter_column(table, column, existing_type=sa.BigInteger(), type_=sa.Integer())
