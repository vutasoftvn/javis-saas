"""add_phone_to_users

Revision ID: 7a1f2c9d4e6b
Revises: 3c9fd60ac308
Create Date: 2026-08-09 09:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7a1f2c9d4e6b'
down_revision: Union[str, Sequence[str], None] = '3c9fd60ac308'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('users', sa.Column('phone', sa.String(length=20), nullable=True))
    op.create_index(op.f('ix_users_phone'), 'users', ['phone'], unique=True)
    op.alter_column('users', 'email', existing_type=sa.String(length=255), nullable=True)


def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column('users', 'email', existing_type=sa.String(length=255), nullable=False)
    op.drop_index(op.f('ix_users_phone'), table_name='users')
    op.drop_column('users', 'phone')
