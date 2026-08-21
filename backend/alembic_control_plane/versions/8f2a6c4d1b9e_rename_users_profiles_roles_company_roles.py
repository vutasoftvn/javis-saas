"""rename platform_users/company_memberships, add roles + profiles

Revision ID: 8f2a6c4d1b9e
Revises: 364cffc3b459
Create Date: 2026-08-21 00:00:00.000000

Đổi tên bảng cho khớp thuật ngữ chuẩn (users/profiles/roles/company_roles)
và tách role khỏi cột string tự do sang bảng danh mục `roles` có 2 nhóm
(scope='platform': superadmin/admin/support cho đội ngũ COSA; scope='company':
founder/co-founder/user cho company_roles). Xem docs/superpowers/plans/...
kế hoạch đã duyệt cho bối cảnh đầy đủ.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8f2a6c4d1b9e'
down_revision: Union[str, Sequence[str], None] = '364cffc3b459'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SCHEMA = "control_plane"


def upgrade() -> None:
    """Upgrade schema."""
    # --- 1. Rename bang ---
    op.rename_table('platform_users', 'users', schema=SCHEMA)
    op.rename_table('company_memberships', 'company_roles', schema=SCHEMA)

    # Rename index cho khop ten bang moi (naming convention ix_%(table_name)s_...)
    op.execute(f'ALTER INDEX {SCHEMA}.ix_platform_users_email RENAME TO ix_users_email')
    op.execute(f'ALTER INDEX {SCHEMA}.ix_platform_users_phone RENAME TO ix_users_phone')
    op.execute(f'ALTER INDEX {SCHEMA}.ix_platform_users_status RENAME TO ix_users_status')
    op.execute(f'ALTER INDEX {SCHEMA}.ix_platform_users_id RENAME TO ix_users_id')
    op.execute(f'ALTER INDEX {SCHEMA}.ix_company_memberships_user RENAME TO ix_company_roles_user')
    op.execute(f'ALTER INDEX {SCHEMA}.ix_company_memberships_company RENAME TO ix_company_roles_company')
    op.execute(f'ALTER INDEX {SCHEMA}.ix_company_memberships_id RENAME TO ix_company_roles_id')

    # --- 2. Bang danh muc roles ---
    op.create_table(
        'roles',
        sa.Column('id', sa.String(length=50), nullable=False),
        sa.Column('scope', sa.String(length=20), nullable=False),
        sa.Column('level', sa.Integer(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint("scope IN ('platform', 'company')", name='chk_roles_scope'),
        schema=SCHEMA,
    )
    op.execute(
        f"""
        INSERT INTO {SCHEMA}.roles (id, scope, level, description) VALUES
        ('superadmin', 'platform', 3, 'Quan tri toan bo nen tang COSA'),
        ('admin', 'platform', 2, 'Quan tri COSA cap thap hon superadmin'),
        ('support', 'platform', 1, 'Doi ho tro / CSKH cua COSA'),
        ('founder', 'company', 3, 'Nguoi tao / so huu company'),
        ('co-founder', 'company', 2, 'Dong sang lap, duoc founder nang cap'),
        ('user', 'company', 1, 'Nhan vien company - mac dinh')
        """
    )

    # --- 3. Bang profiles (tach full_name/avatar_url khoi users) ---
    op.create_table(
        'profiles',
        sa.Column('user_id', sa.BigInteger(), nullable=False),
        sa.Column('full_name', sa.String(length=255), nullable=True),
        sa.Column('avatar_url', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['user_id'], [f'{SCHEMA}.users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('user_id'),
        schema=SCHEMA,
    )
    op.execute(
        f"""
        INSERT INTO {SCHEMA}.profiles (user_id, full_name, avatar_url, created_at, updated_at)
        SELECT id, full_name, avatar_url, now(), now() FROM {SCHEMA}.users
        """
    )
    op.drop_column('users', 'full_name', schema=SCHEMA)
    op.drop_column('users', 'avatar_url', schema=SCHEMA)

    # --- 4. users.platform_role_id (thay is_platform_admin bool) ---
    op.add_column(
        'users',
        sa.Column('platform_role_id', sa.String(length=50), nullable=True),
        schema=SCHEMA,
    )
    op.create_foreign_key(
        'fk_users_platform_role_id_roles', 'users', 'roles',
        ['platform_role_id'], ['id'], source_schema=SCHEMA, referent_schema=SCHEMA,
    )
    op.execute(
        f"UPDATE {SCHEMA}.users SET platform_role_id = 'admin' WHERE is_platform_admin = true"
    )

    # --- 5. company_roles.role_id (thay platform_role string tu do) ---
    op.add_column(
        'company_roles',
        sa.Column('role_id', sa.String(length=50), nullable=True),
        schema=SCHEMA,
    )
    op.execute(
        f"""
        UPDATE {SCHEMA}.company_roles SET role_id = CASE platform_role
            WHEN 'owner' THEN 'founder'
            WHEN 'admin' THEN 'co-founder'
            ELSE 'user'
        END
        """
    )
    op.alter_column('company_roles', 'role_id', nullable=False, schema=SCHEMA)
    op.create_foreign_key(
        'fk_company_roles_role_id_roles', 'company_roles', 'roles',
        ['role_id'], ['id'], source_schema=SCHEMA, referent_schema=SCHEMA,
    )
    op.create_check_constraint(
        'chk_company_roles_role_id',
        'company_roles',
        "role_id IN ('founder', 'co-founder', 'user')",
        schema=SCHEMA,
    )
    op.drop_column('company_roles', 'platform_role', schema=SCHEMA)


def downgrade() -> None:
    """Downgrade schema."""
    op.add_column(
        'company_roles',
        sa.Column('platform_role', sa.String(length=50), nullable=False, server_default='member'),
        schema=SCHEMA,
    )
    op.execute(
        f"""
        UPDATE {SCHEMA}.company_roles SET platform_role = CASE role_id
            WHEN 'founder' THEN 'owner'
            WHEN 'co-founder' THEN 'admin'
            ELSE 'member'
        END
        """
    )
    op.alter_column('company_roles', 'platform_role', server_default=None, schema=SCHEMA)
    op.drop_constraint('chk_company_roles_role_id', 'company_roles', schema=SCHEMA)
    op.drop_constraint('fk_company_roles_role_id_roles', 'company_roles', schema=SCHEMA, type_='foreignkey')
    op.drop_column('company_roles', 'role_id', schema=SCHEMA)

    op.drop_constraint('fk_users_platform_role_id_roles', 'users', schema=SCHEMA, type_='foreignkey')
    op.drop_column('users', 'platform_role_id', schema=SCHEMA)

    op.add_column('users', sa.Column('avatar_url', sa.Text(), nullable=True), schema=SCHEMA)
    op.add_column('users', sa.Column('full_name', sa.String(length=255), nullable=True), schema=SCHEMA)
    op.execute(
        f"""
        UPDATE {SCHEMA}.users u SET full_name = p.full_name, avatar_url = p.avatar_url
        FROM {SCHEMA}.profiles p WHERE p.user_id = u.id
        """
    )
    op.drop_table('profiles', schema=SCHEMA)
    op.drop_table('roles', schema=SCHEMA)

    op.execute(f'ALTER INDEX {SCHEMA}.ix_company_roles_id RENAME TO ix_company_memberships_id')
    op.execute(f'ALTER INDEX {SCHEMA}.ix_company_roles_company RENAME TO ix_company_memberships_company')
    op.execute(f'ALTER INDEX {SCHEMA}.ix_company_roles_user RENAME TO ix_company_memberships_user')
    op.execute(f'ALTER INDEX {SCHEMA}.ix_users_id RENAME TO ix_platform_users_id')
    op.execute(f'ALTER INDEX {SCHEMA}.ix_users_status RENAME TO ix_platform_users_status')
    op.execute(f'ALTER INDEX {SCHEMA}.ix_users_phone RENAME TO ix_platform_users_phone')
    op.execute(f'ALTER INDEX {SCHEMA}.ix_users_email RENAME TO ix_platform_users_email')

    op.rename_table('company_roles', 'company_memberships', schema=SCHEMA)
    op.rename_table('users', 'platform_users', schema=SCHEMA)
