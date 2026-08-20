"""backfill and require ordered idempotent RunEvent fields

Revision ID: c4e01c5a0004
Revises: c3e01c5a0003
Create Date: 2026-08-20 20:15:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c4e01c5a0004"
down_revision: Union[str, Sequence[str], None] = "c3e01c5a0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        WITH ordered AS (
          SELECT id, row_number() OVER (
            PARTITION BY run_id ORDER BY created_at, id
          ) AS allocated_sequence
          FROM run_events
          WHERE sequence IS NULL
        )
        UPDATE run_events AS event
        SET sequence = ordered.allocated_sequence
        FROM ordered
        WHERE event.id = ordered.id
        """
    )
    op.execute(
        "UPDATE run_events "
        "SET event_key = 'legacy:' || id::text "
        "WHERE event_key IS NULL"
    )
    op.alter_column(
        "run_events",
        "sequence",
        existing_type=sa.Integer(),
        nullable=False,
    )
    op.alter_column(
        "run_events",
        "event_key",
        existing_type=sa.String(length=255),
        nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "run_events",
        "event_key",
        existing_type=sa.String(length=255),
        nullable=True,
    )
    op.alter_column(
        "run_events",
        "sequence",
        existing_type=sa.Integer(),
        nullable=True,
    )
