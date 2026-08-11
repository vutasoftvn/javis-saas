"""add retry_count to chunking_jobs

Revision ID: 0cb6b8a3b033
Revises: 9a470e50097b
Create Date: 2026-08-11 22:09:43.517476

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0cb6b8a3b033'
down_revision: Union[str, Sequence[str], None] = '9a470e50097b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'chunking_jobs',
        sa.Column('retry_count', sa.Integer(), nullable=False, server_default='0'),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('chunking_jobs', 'retry_count')
