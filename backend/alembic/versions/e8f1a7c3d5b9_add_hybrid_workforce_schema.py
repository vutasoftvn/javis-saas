"""add hybrid workforce schema

Revision ID: e8f1a7c3d5b9
Revises: d2e5f8a4c9b1
Create Date: 2026-08-11 15:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'e8f1a7c3d5b9'
down_revision: Union[str, Sequence[str], None] = 'd2e5f8a4c9b1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('organizations',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('workspace_id', sa.Uuid(), nullable=False),
    sa.Column('name', sa.String(length=255), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('workspace_id')
    )
    op.create_index(op.f('ix_organizations_workspace_id'), 'organizations', ['workspace_id'], unique=True)

    op.create_table('departments',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('organization_id', sa.Uuid(), nullable=False),
    sa.Column('name', sa.String(length=255), nullable=False),
    sa.Column('is_ai_only', sa.Boolean(), nullable=False),
    sa.Column('capability_domain', sa.String(length=50), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_departments_organization_id'), 'departments', ['organization_id'], unique=False)

    op.create_table('workforce_members',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('organization_id', sa.Uuid(), nullable=False),
    sa.Column('member_type', sa.String(length=20), nullable=False),
    sa.Column('human_user_id', sa.Uuid(), nullable=True),
    sa.Column('agent_id', sa.Uuid(), nullable=True),
    sa.Column('role_title', sa.String(length=255), nullable=False),
    sa.Column('status', sa.String(length=50), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['agent_id'], ['agents.id'], ),
    sa.ForeignKeyConstraint(['human_user_id'], ['users.id'], ),
    sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_workforce_members_organization_id'), 'workforce_members', ['organization_id'], unique=False)
    op.create_index(op.f('ix_workforce_members_human_user_id'), 'workforce_members', ['human_user_id'], unique=False)
    op.create_index(op.f('ix_workforce_members_agent_id'), 'workforce_members', ['agent_id'], unique=False)

    op.create_table('department_memberships',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('member_id', sa.Uuid(), nullable=False),
    sa.Column('department_id', sa.Uuid(), nullable=False),
    sa.Column('role', sa.String(length=50), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['department_id'], ['departments.id'], ),
    sa.ForeignKeyConstraint(['member_id'], ['workforce_members.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_department_memberships_member_id'), 'department_memberships', ['member_id'], unique=False)
    op.create_index(op.f('ix_department_memberships_department_id'), 'department_memberships', ['department_id'], unique=False)

    op.create_table('agent_relations',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('agent_id', sa.Uuid(), nullable=False),
    sa.Column('related_member_id', sa.Uuid(), nullable=False),
    sa.Column('relation', sa.String(length=50), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['agent_id'], ['agents.id'], ),
    sa.ForeignKeyConstraint(['related_member_id'], ['workforce_members.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_agent_relations_agent_id'), 'agent_relations', ['agent_id'], unique=False)
    op.create_index(op.f('ix_agent_relations_related_member_id'), 'agent_relations', ['related_member_id'], unique=False)

    # Extends the existing `tasks` table instead of a parallel `work_items`
    # table (blueprint §150) - additive/nullable, no existing row is touched
    # and no existing query needs these columns to keep working.
    op.add_column('tasks', sa.Column('assignee_member_id', sa.Uuid(), nullable=True))
    op.add_column('tasks', sa.Column('owner_member_id', sa.Uuid(), nullable=True))
    op.add_column('tasks', sa.Column('execution_mode', sa.String(length=20), nullable=True))
    op.create_foreign_key('fk_tasks_assignee_member_id', 'tasks', 'workforce_members', ['assignee_member_id'], ['id'])
    op.create_foreign_key('fk_tasks_owner_member_id', 'tasks', 'workforce_members', ['owner_member_id'], ['id'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint('fk_tasks_owner_member_id', 'tasks', type_='foreignkey')
    op.drop_constraint('fk_tasks_assignee_member_id', 'tasks', type_='foreignkey')
    op.drop_column('tasks', 'execution_mode')
    op.drop_column('tasks', 'owner_member_id')
    op.drop_column('tasks', 'assignee_member_id')

    op.drop_index(op.f('ix_agent_relations_related_member_id'), table_name='agent_relations')
    op.drop_index(op.f('ix_agent_relations_agent_id'), table_name='agent_relations')
    op.drop_table('agent_relations')

    op.drop_index(op.f('ix_department_memberships_department_id'), table_name='department_memberships')
    op.drop_index(op.f('ix_department_memberships_member_id'), table_name='department_memberships')
    op.drop_table('department_memberships')

    op.drop_index(op.f('ix_workforce_members_agent_id'), table_name='workforce_members')
    op.drop_index(op.f('ix_workforce_members_human_user_id'), table_name='workforce_members')
    op.drop_index(op.f('ix_workforce_members_organization_id'), table_name='workforce_members')
    op.drop_table('workforce_members')

    op.drop_index(op.f('ix_departments_organization_id'), table_name='departments')
    op.drop_table('departments')

    op.drop_index(op.f('ix_organizations_workspace_id'), table_name='organizations')
    op.drop_table('organizations')
