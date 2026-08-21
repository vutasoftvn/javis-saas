"""split agent_runtime and integrations schemas out of public

Revision ID: ce172b817a1d
Revises: v13_062_vault_document_metadata
Create Date: 2026-08-21 19:44:53.215658

Tach 79 bang khoi schema public thanh 2 schema moi theo do doc lap thuc te
(FK graph): agent_runtime (54 bang - workforce/agent governance/memory/
sandbox, it phu thuoc nguoc) va integrations (25 bang - connectors/chat).
Dung ALTER TABLE ... SET SCHEMA (thao tac metadata-only trong Postgres,
KHONG copy du lieu, khong downtime) - KHONG dung autogenerate vi no se sinh
nham DROP+CREATE (mat du lieu) thay vi nhan ra day la doi schema cua bang
da ton tai.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ce172b817a1d'
down_revision: Union[str, Sequence[str], None] = 'v13_062_vault_document_metadata'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

AGENT_RUNTIME_TABLES = ['agent_aliases', 'agent_approvals', 'agent_budgets', 'agent_definitions', 'agent_events', 'agent_goals', 'agent_heartbeats', 'agent_hierarchies', 'agent_memory_engines', 'agent_memory_entries', 'agent_memory_scopes', 'agent_plan_steps', 'agent_plans', 'agent_proposals', 'agent_routines', 'agent_runs', 'agent_tool_calls', 'agent_tool_permissions', 'approval_requests', 'automation_callbacks', 'automation_definitions', 'automation_runs', 'capability_grants', 'cost_ledger_entries', 'decision_records', 'delegation_jobs', 'escalation_records', 'execution_jobs', 'execution_steps', 'extension_registrations', 'founder_decisions', 'global_skill_registry', 'job_outcomes', 'memory_candidates', 'memory_evaluations', 'memory_health_snapshots', 'memory_promotions', 'memory_sync_records', 'mission_resume_jobs', 'platform_agent_runs', 'platform_agent_steps', 'platform_prompt_templates', 'platform_prompt_versions', 'platform_secret_refs', 'platform_tool_versions', 'protected_resource_revisions', 'protected_resources', 'routine_executions', 'runtime_sessions', 'sandbox_policies', 'skill_trajectory_candidates', 'tool_definitions', 'unified_permissions', 'work_products']
INTEGRATIONS_TABLES = ['ai_runs', 'chat_messages', 'chat_sessions', 'chatbot_conversations', 'chatbots', 'developer_jobs', 'device_credentials', 'devices', 'email_approvals', 'job_leases', 'mcp_connections', 'outbox', 'plugins', 'realtime_events', 'realtime_sessions', 'task_workflow_bindings', 'voice_usage_records', 'workflow_approvals', 'workflow_definitions', 'workflow_runs', 'workflow_steps', 'workflow_versions', 'workspace_plugins', 'workspace_secrets', 'zalo_qr_sessions']


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("CREATE SCHEMA IF NOT EXISTS agent_runtime")
    op.execute("CREATE SCHEMA IF NOT EXISTS integrations")

    for table in AGENT_RUNTIME_TABLES:
        op.execute(f"ALTER TABLE public.{table} SET SCHEMA agent_runtime")
    for table in INTEGRATIONS_TABLES:
        op.execute(f"ALTER TABLE public.{table} SET SCHEMA integrations")

    # javis_app can BE the connecting role that runs this migration (it owns
    # public already) - grant it full rights on the 2 new schemas too, same
    # pattern as deploy/postgres/init/01-create-app-roles.sql for `public`.
    op.execute("GRANT ALL ON SCHEMA agent_runtime TO javis_app")
    op.execute("GRANT ALL ON ALL TABLES IN SCHEMA agent_runtime TO javis_app")
    op.execute("ALTER DEFAULT PRIVILEGES IN SCHEMA agent_runtime GRANT ALL ON TABLES TO javis_app")
    op.execute("GRANT ALL ON SCHEMA integrations TO javis_app")
    op.execute("GRANT ALL ON ALL TABLES IN SCHEMA integrations TO javis_app")
    op.execute("ALTER DEFAULT PRIVILEGES IN SCHEMA integrations GRANT ALL ON TABLES TO javis_app")


def downgrade() -> None:
    """Downgrade schema."""
    for table in AGENT_RUNTIME_TABLES:
        op.execute(f"ALTER TABLE agent_runtime.{table} SET SCHEMA public")
    for table in INTEGRATIONS_TABLES:
        op.execute(f"ALTER TABLE integrations.{table} SET SCHEMA public")

    op.execute("DROP SCHEMA IF EXISTS agent_runtime CASCADE")
    op.execute("DROP SCHEMA IF EXISTS integrations CASCADE")
