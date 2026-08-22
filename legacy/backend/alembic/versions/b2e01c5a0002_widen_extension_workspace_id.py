"""widen extension workspace id for Snowflake identifiers

Revision ID: b2e01c5a0002
Revises: b1e01c5a0001
Create Date: 2026-08-20 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b2e01c5a0002"
down_revision: Union[str, Sequence[str], None] = "b1e01c5a0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "extension_registrations",
        "workspace_id",
        existing_type=sa.Integer(),
        type_=sa.BigInteger(),
        existing_nullable=False,
        postgresql_using="workspace_id::bigint",
    )


def downgrade() -> None:
    op.alter_column(
        "extension_registrations",
        "workspace_id",
        existing_type=sa.BigInteger(),
        type_=sa.Integer(),
        existing_nullable=False,
        postgresql_using="workspace_id::integer",
    )
