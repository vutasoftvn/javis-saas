"""runtime heartbeat used by readiness probes to verify agent-worker activity."""

from alembic import op
import sqlalchemy as sa


revision = "v13_030_worker_heartbeat"
down_revision = "v13_029_chat_session_purpose"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "runtime_heartbeats",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=False),
        sa.Column("component", sa.String(length=100), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("component", name="uq_runtime_heartbeats_component"),
    )
    op.create_index("ix_runtime_heartbeats_component", "runtime_heartbeats", ["component"])


def downgrade() -> None:
    op.drop_index("ix_runtime_heartbeats_component", table_name="runtime_heartbeats")
    op.drop_table("runtime_heartbeats")
