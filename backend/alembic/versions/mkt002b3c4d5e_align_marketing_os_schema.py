"""align_marketing_os_schema - đồng bộ ORM Marketing OS với Postgres + bảng skill_executions

Migration mkt001 tạo bảng theo một bản phác thảo khác với `app/modules/marketing/models.py`
(metric, snapshot, learning, asset, experiment đều lệch cột). Router che lỗi bằng
try/except nên UI luôn rỗng thay vì báo lỗi. Migration này lấy ORM làm chuẩn.

Revision ID: mkt002b3c4d5e
Revises: mkt001a2b3c4
Create Date: 2026-08-10 21:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'mkt002b3c4d5e'
down_revision = 'mkt001a2b3c4'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- marketing_metrics: bổ sung cột ORM cần, giữ metric_value làm giá trị hiện tại
    op.add_column('marketing_metrics', sa.Column('category', sa.String(50), nullable=False, server_default='acquisition'))
    op.add_column('marketing_metrics', sa.Column('previous_value', sa.Float(), nullable=False, server_default='0'))
    op.add_column('marketing_metrics', sa.Column('change_pct', sa.Float(), nullable=False, server_default='0'))
    op.add_column('marketing_metrics', sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False))
    op.alter_column('marketing_metrics', 'unit', server_default='number', nullable=False)
    op.create_unique_constraint(
        'uq_marketing_metric_scope_name', 'marketing_metrics', ['workspace_id', 'brain_id', 'metric_name']
    )
    op.create_index('ix_marketing_metrics_metric_name', 'marketing_metrics', ['metric_name'])

    # --- metric_snapshots: gắn snapshot vào metric cụ thể (lịch sử để vẽ xu hướng)
    op.add_column('metric_snapshots', sa.Column('metric_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key(
        'fk_metric_snapshots_metric_id', 'metric_snapshots', 'marketing_metrics', ['metric_id'], ['id'], ondelete='CASCADE'
    )
    op.create_index('ix_metric_snapshots_metric_id', 'metric_snapshots', ['metric_id'])
    op.create_index('ix_metric_snapshots_snapshot_at', 'metric_snapshots', ['snapshot_at'])

    # --- marketing_learnings: đủ 5 trường của Learning Loop §16
    op.add_column('marketing_learnings', sa.Column('campaign_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column('marketing_learnings', sa.Column('observation', sa.Text(), nullable=False, server_default=''))
    op.add_column('marketing_learnings', sa.Column('hypothesis', sa.Text(), nullable=False, server_default=''))
    op.add_column('marketing_learnings', sa.Column('action', sa.Text(), nullable=False, server_default=''))
    op.add_column('marketing_learnings', sa.Column('result', sa.Text(), nullable=False, server_default=''))
    op.add_column('marketing_learnings', sa.Column('confidence', sa.String(50), nullable=False, server_default='medium'))
    op.add_column('marketing_learnings', sa.Column('reusable_rule', sa.Text(), nullable=True))

    # --- marketing_campaigns: khung thời gian chạy chiến dịch (§9)
    op.add_column('marketing_campaigns', sa.Column('start_date', sa.DateTime(), nullable=True))
    op.add_column('marketing_campaigns', sa.Column('end_date', sa.DateTime(), nullable=True))

    # --- campaign_assets: cần updated_at, workspace_id đã có sẵn từ mkt001
    op.add_column('campaign_assets', sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False))
    op.create_index('ix_campaign_assets_workspace_id', 'campaign_assets', ['workspace_id'])

    # --- marketing_experiments: variant là nội dung dài, thêm learning + evaluation
    op.alter_column('marketing_experiments', 'variant_a', type_=sa.Text(), existing_type=sa.String(255))
    op.alter_column('marketing_experiments', 'variant_b', type_=sa.Text(), existing_type=sa.String(255))
    op.add_column('marketing_experiments', sa.Column('learning', sa.Text(), nullable=True))
    op.add_column('marketing_experiments', sa.Column('evaluation', postgresql.JSONB(), nullable=True))

    # --- skill_executions (§25 Skill Evaluation)
    op.create_table(
        'skill_executions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('workspace_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('workspaces.id', ondelete='CASCADE'), nullable=False),
        sa.Column('brain_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('approval_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('pending_approvals.id', ondelete='SET NULL'), nullable=True),
        sa.Column('capability_id', sa.String(100), nullable=False),
        sa.Column('provider', postgresql.JSONB(), nullable=False),
        sa.Column('task_input', postgresql.JSONB(), nullable=True),
        sa.Column('output', postgresql.JSONB(), nullable=True),
        sa.Column('status', sa.String(50), nullable=False, server_default='simulated'),
        sa.Column('requested_by_agent', sa.String(100), nullable=True),
        sa.Column('latency_ms', sa.Integer(), nullable=True),
        sa.Column('cost', sa.Float(), nullable=True),
        sa.Column('human_rating', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_skill_executions_workspace_id', 'skill_executions', ['workspace_id'])
    op.create_index('ix_skill_executions_capability_id', 'skill_executions', ['capability_id'])


def downgrade() -> None:
    op.drop_table('skill_executions')

    op.drop_column('marketing_experiments', 'evaluation')
    op.drop_column('marketing_experiments', 'learning')
    op.alter_column('marketing_experiments', 'variant_b', type_=sa.String(255), existing_type=sa.Text())
    op.alter_column('marketing_experiments', 'variant_a', type_=sa.String(255), existing_type=sa.Text())

    op.drop_index('ix_campaign_assets_workspace_id', table_name='campaign_assets')
    op.drop_column('campaign_assets', 'updated_at')

    op.drop_column('marketing_campaigns', 'end_date')
    op.drop_column('marketing_campaigns', 'start_date')

    for col in ('reusable_rule', 'confidence', 'result', 'action', 'hypothesis', 'observation', 'campaign_id'):
        op.drop_column('marketing_learnings', col)

    op.drop_index('ix_metric_snapshots_snapshot_at', table_name='metric_snapshots')
    op.drop_index('ix_metric_snapshots_metric_id', table_name='metric_snapshots')
    op.drop_constraint('fk_metric_snapshots_metric_id', 'metric_snapshots', type_='foreignkey')
    op.drop_column('metric_snapshots', 'metric_id')

    op.drop_index('ix_marketing_metrics_metric_name', table_name='marketing_metrics')
    op.drop_constraint('uq_marketing_metric_scope_name', 'marketing_metrics', type_='unique')
    for col in ('updated_at', 'change_pct', 'previous_value', 'category'):
        op.drop_column('marketing_metrics', col)
