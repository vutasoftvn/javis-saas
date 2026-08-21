"""add core.users.role column (synced from control_plane.company_roles)

Revision ID: c3d7e9a2f1b4
Revises: ad0ba92719b0
Create Date: 2026-08-21 00:00:00.000000

Cot `role` khong co CHECK constraint rieng o local - gia tri chi duoc ghi
vao khi lien ket tai khoan local<->central (dong bo tu
control_plane.company_roles.role_id: founder/co-founder/user), khong phai
mot bo gia tri local tu quan ly. Xem docs/superpowers/plans ke hoach da duyet.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c3d7e9a2f1b4'
down_revision: Union[str, Sequence[str], None] = 'ad0ba92719b0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('users', sa.Column('role', sa.String(length=50), nullable=True), schema='core')


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('users', 'role', schema='core')
