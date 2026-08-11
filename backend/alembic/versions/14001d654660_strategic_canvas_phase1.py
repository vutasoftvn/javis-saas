"""strategic_canvas_phase1

Revision ID: 14001d654660
Revises: 7a1f2c9d4e6b
Create Date: 2026-08-09 20:40:03.172430

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '14001d654660'
down_revision: Union[str, Sequence[str], None] = '7a1f2c9d4e6b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # RENAME (không drop/create) strategy_profiles -> strategy_canvases: cùng khái
    # niệm (Phase 2B cũ), chỉ bổ sung name/description/created_by. Postgres giữ
    # nguyên OID nên FK bsc_scorecards.strategy_profile_id tự động trỏ đúng bảng mới,
    # không cần drop/recreate constraint đó.
    op.rename_table('strategy_profiles', 'strategy_canvases')
    op.add_column('strategy_canvases', sa.Column('name', sa.Text(), nullable=True))
    op.execute("UPDATE strategy_canvases SET name = 'Company Strategy' WHERE name IS NULL")
    op.alter_column('strategy_canvases', 'name', nullable=False)
    op.add_column('strategy_canvases', sa.Column('description', sa.Text(), nullable=True))
    op.add_column('strategy_canvases', sa.Column('created_by', sa.Uuid(), nullable=True))
    op.create_foreign_key(None, 'strategy_canvases', 'users', ['created_by'], ['id'])

    op.create_table('evidence_items',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('workspace_id', sa.Uuid(), nullable=False),
    sa.Column('title', sa.String(length=255), nullable=False),
    sa.Column('summary', sa.Text(), nullable=False),
    sa.Column('source_type', sa.String(length=50), nullable=False),
    sa.Column('source_url_or_vault_uri', sa.String(length=1024), nullable=True),
    sa.Column('published_at', sa.DateTime(), nullable=True),
    sa.Column('captured_at', sa.DateTime(), nullable=False),
    sa.Column('reliability', sa.String(length=50), nullable=False),
    sa.Column('tags', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('created_by', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['created_by'], ['users.id'], ),
    sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.CheckConstraint("reliability in ('high','medium','low')", name='ck_evidence_items_reliability')
    )
    op.create_index(op.f('ix_evidence_items_workspace_id'), 'evidence_items', ['workspace_id'], unique=False)
    op.create_table('strategy_revisions',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('canvas_id', sa.Uuid(), nullable=False),
    sa.Column('revision_no', sa.Integer(), nullable=False),
    sa.Column('status', sa.String(length=50), nullable=False),
    sa.Column('parent_revision_id', sa.Uuid(), nullable=True),
    sa.Column('created_by', sa.Uuid(), nullable=False),
    sa.Column('approved_by', sa.Uuid(), nullable=True),
    sa.Column('approved_at', sa.DateTime(), nullable=True),
    sa.Column('stale_reason', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['approved_by'], ['users.id'], ),
    sa.ForeignKeyConstraint(['canvas_id'], ['strategy_canvases.id'], ),
    sa.ForeignKeyConstraint(['created_by'], ['users.id'], ),
    sa.ForeignKeyConstraint(['parent_revision_id'], ['strategy_revisions.id'], use_alter=True),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('canvas_id', 'revision_no', name='uix_strategy_revision_canvas_no'),
    sa.CheckConstraint(
        "status in ('draft','in_review','approved','changes_requested','superseded','archived')",
        name='ck_strategy_revisions_status'
    )
    )
    op.create_index(op.f('ix_strategy_revisions_canvas_id'), 'strategy_revisions', ['canvas_id'], unique=False)
    # Bất biến §3.1: tối đa 1 revision `approved` cho mỗi canvas.
    op.create_index(
        'one_approved_revision_per_canvas', 'strategy_revisions', ['canvas_id'],
        unique=True, postgresql_where=sa.text("status = 'approved'")
    )
    op.create_table('strategy_foundations',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('strategy_revision_id', sa.Uuid(), nullable=False),
    sa.Column('vision', sa.Text(), nullable=True),
    sa.Column('mission', sa.Text(), nullable=True),
    sa.Column('status', sa.String(length=50), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['strategy_revision_id'], ['strategy_revisions.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.CheckConstraint("status in ('draft','approved')", name='ck_strategy_foundations_status'),
    sa.CheckConstraint("vision is null or char_length(vision) between 20 and 500", name='ck_strategy_foundations_vision_len'),
    sa.CheckConstraint("mission is null or char_length(mission) between 20 and 500", name='ck_strategy_foundations_mission_len')
    )
    op.create_index(op.f('ix_strategy_foundations_strategy_revision_id'), 'strategy_foundations', ['strategy_revision_id'], unique=True)
    op.create_table('core_values',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('foundation_id', sa.Uuid(), nullable=False),
    sa.Column('slot_no', sa.Integer(), nullable=False),
    sa.Column('title', sa.String(length=255), nullable=False),
    sa.Column('description', sa.Text(), nullable=False),
    sa.Column('decision_rule', sa.Text(), nullable=False),
    sa.ForeignKeyConstraint(['foundation_id'], ['strategy_foundations.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('foundation_id', 'slot_no', name='uix_core_value_foundation_slot'),
    sa.CheckConstraint('slot_no between 1 and 3', name='ck_core_values_slot_no')
    )
    op.create_index(op.f('ix_core_values_foundation_id'), 'core_values', ['foundation_id'], unique=False)

    op.add_column('context_pack_sources', sa.Column('evidence_id', sa.Uuid(), nullable=True))
    op.alter_column('context_pack_sources', 'revision_id',
               existing_type=sa.UUID(),
               nullable=True)
    op.create_index(op.f('ix_context_pack_sources_evidence_id'), 'context_pack_sources', ['evidence_id'], unique=False)
    op.create_foreign_key(None, 'context_pack_sources', 'evidence_items', ['evidence_id'], ['id'])

    op.add_column('context_packs', sa.Column('strategy_revision_id', sa.Uuid(), nullable=True))
    op.add_column('context_packs', sa.Column('business_context', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('context_packs', sa.Column('internal_resources', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('context_packs', sa.Column('approved_at', sa.DateTime(), nullable=True))
    op.add_column('context_packs', sa.Column(
        'updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')
    ))
    op.alter_column('context_packs', 'updated_at', server_default=None)
    op.create_index(op.f('ix_context_packs_strategy_revision_id'), 'context_packs', ['strategy_revision_id'], unique=False)
    op.create_foreign_key(None, 'context_packs', 'strategy_revisions', ['strategy_revision_id'], ['id'])
    # Rà soát dữ liệu thật trước khi siết CHECK này trên môi trường đã có dữ liệu
    # (SELECT DISTINCT status FROM context_packs) - dev DB hiện đang rỗng, đã kiểm tra an toàn.
    op.create_check_constraint(
        'ck_context_packs_status', 'context_packs',
        "status in ('draft','ready_for_review','approved','stale','superseded')"
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint('ck_context_packs_status', 'context_packs', type_='check')
    op.drop_constraint('context_packs_strategy_revision_id_fkey', 'context_packs', type_='foreignkey')
    op.drop_index(op.f('ix_context_packs_strategy_revision_id'), table_name='context_packs')
    op.drop_column('context_packs', 'updated_at')
    op.drop_column('context_packs', 'approved_at')
    op.drop_column('context_packs', 'internal_resources')
    op.drop_column('context_packs', 'business_context')
    op.drop_column('context_packs', 'strategy_revision_id')

    op.drop_constraint('context_pack_sources_evidence_id_fkey', 'context_pack_sources', type_='foreignkey')
    op.drop_index(op.f('ix_context_pack_sources_evidence_id'), table_name='context_pack_sources')
    op.alter_column('context_pack_sources', 'revision_id',
               existing_type=sa.UUID(),
               nullable=False)
    op.drop_column('context_pack_sources', 'evidence_id')

    op.drop_index(op.f('ix_core_values_foundation_id'), table_name='core_values')
    op.drop_table('core_values')
    op.drop_index(op.f('ix_strategy_foundations_strategy_revision_id'), table_name='strategy_foundations')
    op.drop_table('strategy_foundations')
    op.drop_index('one_approved_revision_per_canvas', table_name='strategy_revisions')
    op.drop_index(op.f('ix_strategy_revisions_canvas_id'), table_name='strategy_revisions')
    op.drop_table('strategy_revisions')
    op.drop_index(op.f('ix_evidence_items_workspace_id'), table_name='evidence_items')
    op.drop_table('evidence_items')

    # Đảo ngược rename: strategy_canvases -> strategy_profiles (sau khi đã drop hết
    # bảng con FK vào strategy_canvases ở trên).
    op.drop_constraint('strategy_canvases_created_by_fkey', 'strategy_canvases', type_='foreignkey')
    op.drop_column('strategy_canvases', 'created_by')
    op.drop_column('strategy_canvases', 'description')
    op.drop_column('strategy_canvases', 'name')
    op.rename_table('strategy_canvases', 'strategy_profiles')
    # ### end Alembic commands ###
