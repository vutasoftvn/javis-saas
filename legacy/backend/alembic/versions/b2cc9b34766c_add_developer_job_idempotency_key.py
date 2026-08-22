"""add idempotency_key to developer_jobs (mCOSA V12.2 §70/§90.11 voice command idempotency)

Revision ID: b2cc9b34766c
Revises: f3a9c1e7b2d4
Create Date: 2026-08-12 00:00:00.000001

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b2cc9b34766c'
down_revision: Union[str, Sequence[str], None] = 'f3a9c1e7b2d4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('developer_jobs', sa.Column('idempotency_key', sa.String(length=255), nullable=True))
    op.create_unique_constraint(
        'uix_developer_job_workspace_idempotency_key',
        'developer_jobs',
        ['workspace_id', 'idempotency_key'],
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint('uix_developer_job_workspace_idempotency_key', 'developer_jobs', type_='unique')
    op.drop_column('developer_jobs', 'idempotency_key')
