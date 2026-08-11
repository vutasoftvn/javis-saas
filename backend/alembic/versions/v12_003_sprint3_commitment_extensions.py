"""mcosa v12 sprint 3 weekly commitment extensions

Revision ID: v12_003_sprint3
Revises: v12_002_sprint2
Create Date: 2026-08-11 19:50:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'v12_003_sprint3'
down_revision: Union[str, Sequence[str], None] = 'v12_002_sprint2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'weekly_commitments',
        sa.Column('commitment_owner_type', sa.String(length=50), nullable=True, server_default='FOUNDER')
    )
    op.add_column(
        'weekly_commitments',
        sa.Column('execution_mode', sa.String(length=50), nullable=True, server_default='MANUAL')
    )


def downgrade() -> None:
    op.drop_column('weekly_commitments', 'execution_mode')
    op.drop_column('weekly_commitments', 'commitment_owner_type')
