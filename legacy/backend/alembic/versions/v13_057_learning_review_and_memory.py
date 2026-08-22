"""Learning Review Worker + Memory consolidation (G1 §6-8 / G3 Phase 1E).

- `agent_proposals`: adds the Learning Candidate fields (domain/target_key/
  diff_jsonb/confidence/evidence_ids_jsonb/source_outcome_id) so
  `proposal_type="learning_candidate"` rows can be written without a new
  table, per G2 §2.5.
- `agent_memory_entries`: adds `domain`/`provenance_jsonb` so
  `LearningWriter.record_learning()` can be redirected here instead of the
  separate `AgentMemoryItem`/`agent_business_memories` table it used to
  write to.
- Drops `agent_business_memories` (`AgentMemoryItem`): zero production
  readers, exactly one production writer (`LearningWriter`, itself never
  called from production code, only tests) - confirmed via full-backend
  grep before this migration was written. Its one writer is redirected to
  `agent_memory_entries` in this same change, so no data migration is
  needed; a genuinely idle table is safe to drop outright, per the
  standing "don't keep code/tables nothing uses" instruction for this
  refactor pass.

Revision ID: v13_057_learning_memory
Revises: v13_056_skill_registry_v
Create Date: 2026-08-20 12:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "v13_057_learning_memory"
down_revision: Union[str, Sequence[str], None] = "v13_056_skill_registry_v"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_PROPOSAL_COLUMNS = (
    ("domain", sa.String(length=50), True),
    ("target_key", sa.String(length=150), True),
    ("diff_jsonb", postgresql.JSONB(astext_type=sa.Text()), True),
    ("confidence", sa.Float(), True),
    ("evidence_ids_jsonb", postgresql.JSONB(astext_type=sa.Text()), True),
    ("source_outcome_id", sa.BigInteger(), True),
)

_MEMORY_COLUMNS = (
    ("domain", sa.String(length=50), True),
    ("provenance_jsonb", postgresql.JSONB(astext_type=sa.Text()), True),
)


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    existing_proposal_columns = {c["name"] for c in inspector.get_columns("agent_proposals")}
    with op.batch_alter_table("agent_proposals") as batch_op:
        for name, col_type, nullable in _PROPOSAL_COLUMNS:
            if name in existing_proposal_columns:
                continue
            batch_op.add_column(sa.Column(name, col_type, nullable=nullable))

    existing_memory_columns = {c["name"] for c in inspector.get_columns("agent_memory_entries")}
    with op.batch_alter_table("agent_memory_entries") as batch_op:
        for name, col_type, nullable in _MEMORY_COLUMNS:
            if name in existing_memory_columns:
                continue
            batch_op.add_column(sa.Column(name, col_type, nullable=nullable))

    if "agent_business_memories" in inspector.get_table_names():
        op.drop_table("agent_business_memories")


def downgrade() -> None:
    op.create_table(
        "agent_business_memories",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=False),
        sa.Column("workspace_id", sa.BigInteger(), sa.ForeignKey("workspaces.id"), nullable=False, index=True),
        sa.Column("company_id", sa.BigInteger(), nullable=True, index=True),
        sa.Column("user_id", sa.BigInteger(), sa.ForeignKey("users.id"), nullable=True, index=True),
        sa.Column("memory_type", sa.String(length=50), nullable=False),
        sa.Column("domain", sa.String(length=50), nullable=False, server_default="general"),
        sa.Column("key", sa.String(length=255), nullable=False, index=True),
        sa.Column("value_jsonb", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("provenance_jsonb", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    conn = op.get_bind()
    inspector = sa.inspect(conn)

    existing_memory_columns = {c["name"] for c in inspector.get_columns("agent_memory_entries")}
    with op.batch_alter_table("agent_memory_entries") as batch_op:
        for name, _col_type, _nullable in reversed(_MEMORY_COLUMNS):
            if name in existing_memory_columns:
                batch_op.drop_column(name)

    existing_proposal_columns = {c["name"] for c in inspector.get_columns("agent_proposals")}
    with op.batch_alter_table("agent_proposals") as batch_op:
        for name, _col_type, _nullable in reversed(_PROPOSAL_COLUMNS):
            if name in existing_proposal_columns:
                batch_op.drop_column(name)
