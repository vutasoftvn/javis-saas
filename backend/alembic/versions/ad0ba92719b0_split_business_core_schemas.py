"""split business core domain schemas out of public

Revision ID: ad0ba92719b0
Revises: ce172b817a1d
Create Date: 2026-08-21 00:00:00.000000

Tach 201 bang con lai trong schema public thanh 11 schema theo domain
nghiep vu (khop CLAUDE.md Business Core): finance, sales, marketing, legal,
validation, strategy, operating, knowledge, policy_funding, core, runtime_ops.
Chi con `alembic_version` o lai public.

Dung ALTER TABLE ... SET SCHEMA (thao tac metadata-only trong Postgres,
KHONG copy du lieu, khong downtime, khong dung autogenerate vi se sinh nham
DROP+CREATE thay vi doi schema cua bang da ton tai) - cung pattern voi
ce172b817a1d_split_agent_runtime_and_integrations_.py.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ad0ba92719b0'
down_revision: Union[str, Sequence[str], None] = 'ce172b817a1d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

CORE_TABLES = ['agent_relations', 'audit_logs', 'business_asset_overrides', 'business_packs', 'department_memberships', 'departments', 'deployments', 'feature_flags', 'navigation_groups', 'navigation_items', 'offerings', 'operating_units', 'organizations', 'runtime_heartbeats', 'technology_radar_items', 'users', 'workforce_members', 'workforce_relations', 'workspace_domains', 'workspace_members', 'workspaces']
FINANCE_TABLES = ['accounting_book_templates', 'accounting_coa_mappings', 'accounting_documents', 'accounting_fiscal_profiles', 'accounting_periods', 'accounting_profiles', 'accounting_records', 'accounting_regime_transition_logs', 'accounting_regulation_versions', 'accounting_regulations', 'finance_exceptions', 'finance_management_snapshots', 'financial_statement_templates', 'financial_transactions']
KNOWLEDGE_TABLES = ['attachments', 'brains', 'chunking_jobs', 'document_chunks', 'knowledge_objects', 'knowledge_relations', 'vault_documents', 'vault_revisions']
LEGAL_TABLES = ['legal_annotations', 'legal_checklist_items', 'legal_obligations', 'legal_sources']
MARKETING_TABLES = ['assumptions', 'campaign_assets', 'canvas_revisions', 'customer_interviews', 'evidence', 'form_definitions', 'form_submissions', 'knowledge_statements', 'marketing_attributions', 'marketing_campaigns', 'marketing_contexts', 'marketing_decisions', 'marketing_experiments', 'marketing_learnings', 'marketing_loops', 'marketing_metrics', 'marketing_objectives', 'marketing_recommendations', 'metric_snapshots', 'pending_approvals', 'skill_executions', 'skill_registries', 'web_events']
OPERATING_TABLES = ['celebration_records', 'cycle_contracts', 'cycle_reviews', 'cycle_stages', 'lessons', 'methodology_plans', 'milestones', 'tactical_execution_items', 'task_dependencies', 'task_schedules', 'tasks', 'twelve_week_cycles', 'weekly_accountability_reviews', 'weekly_commitments', 'weekly_plans', 'weekly_reviews']
POLICY_FUNDING_TABLES = ['admin_policy_inboxes', 'policy_application_sections', 'policy_applications', 'policy_change_proposals', 'policy_eligibility_rules', 'policy_program_claims', 'policy_program_rounds', 'policy_programs', 'policy_source_documents', 'policy_source_snapshots', 'policy_verifications', 'project_compliance_obligations', 'project_cost_allocations', 'project_eligibility_evaluations', 'project_funding_awards', 'project_funding_needs', 'project_missing_requirements', 'project_program_matches', 'project_stage_assessments', 'project_trl_assessments']
RUNTIME_OPS_TABLES = ['agents', 'artifacts', 'blockers', 'handoffs', 'local_entitlement_snapshots', 'needs_you_items', 'outcome_runs', 'outcomes', 'platform_inbox', 'platform_outbox', 'run_events', 'run_steps', 'runtime_checkpoints', 'work_reviews']
SALES_TABLES = ['accounts', 'contacts', 'customers', 'sales_activities', 'sales_leads', 'sales_opportunities']
STRATEGY_TABLES = ['analysis_imports', 'bsc_goals', 'bsc_scorecards', 'capability_definitions', 'capacity_allocations', 'context_pack_sources', 'context_packs', 'core_values', 'evidence_items', 'evidences', 'founder_attention_allocations', 'founder_profiles', 'gate_decisions', 'hypotheses', 'initiative_key_result_links', 'initiatives', 'key_results', 'metric_checkins', 'metrics', 'milestone_evidence', 'model_profile_overrides', 'model_runs_audit', 'mvp_stages', 'next_action_candidates', 'next_action_rankings', 'okr_cycles', 'okr_links', 'okr_objectives', 'pestel_items', 'pestel_signals', 'portfolio_cycles', 'portfolio_dependencies', 'portfolio_options', 'portfolio_projects', 'portfolio_synergies', 'portfolios', 'premature_scaling_alerts', 'project_classifications', 'project_pestel_impacts', 'projects', 'prompt_templates', 'stage_assignments', 'stage_revisions', 'stage_service_assessments', 'stage_transition_audits', 'strategic_decisions', 'strategic_objective_links', 'strategic_objectives', 'strategy_analyses', 'strategy_audit_events', 'strategy_canvases', 'strategy_foundations', 'strategy_revisions', 'swot_items', 'tows_options', 'workspace_agents', 'workspace_template_versions', 'workspace_templates']
VALIDATION_TABLES = ['dimension_states', 'field_revisions', 'project_stage_history', 'structured_claims', 'validation_assumptions', 'validation_customer_contacts', 'validation_decisions', 'validation_early_adopters', 'validation_evidence', 'validation_experiments', 'validation_hypotheses', 'validation_interview_sessions', 'validation_pain_patterns', 'validation_problem_scorecards', 'validation_reviews', 'validation_sessions', 'validation_verbatim_quotes']

SCHEMA_TABLES = {
    "core": CORE_TABLES,
    "finance": FINANCE_TABLES,
    "knowledge": KNOWLEDGE_TABLES,
    "legal": LEGAL_TABLES,
    "marketing": MARKETING_TABLES,
    "operating": OPERATING_TABLES,
    "policy_funding": POLICY_FUNDING_TABLES,
    "runtime_ops": RUNTIME_OPS_TABLES,
    "sales": SALES_TABLES,
    "strategy": STRATEGY_TABLES,
    "validation": VALIDATION_TABLES,
}


def upgrade() -> None:
    """Upgrade schema."""
    for schema in SCHEMA_TABLES:
        op.execute(f"CREATE SCHEMA IF NOT EXISTS {schema}")

    for schema, tables in SCHEMA_TABLES.items():
        for table in tables:
            op.execute(f"ALTER TABLE public.{table} SET SCHEMA {schema}")

    for schema in SCHEMA_TABLES:
        op.execute(f"GRANT ALL ON SCHEMA {schema} TO javis_app")
        op.execute(f"GRANT ALL ON ALL TABLES IN SCHEMA {schema} TO javis_app")
        op.execute(f"GRANT ALL ON ALL SEQUENCES IN SCHEMA {schema} TO javis_app")
        op.execute(f"ALTER DEFAULT PRIVILEGES IN SCHEMA {schema} GRANT ALL ON TABLES TO javis_app")
        op.execute(f"ALTER DEFAULT PRIVILEGES IN SCHEMA {schema} GRANT ALL ON SEQUENCES TO javis_app")


def downgrade() -> None:
    """Downgrade schema."""
    for schema, tables in SCHEMA_TABLES.items():
        for table in tables:
            op.execute(f"ALTER TABLE {schema}.{table} SET SCHEMA public")

    for schema in SCHEMA_TABLES:
        op.execute(f"DROP SCHEMA IF EXISTS {schema} CASCADE")
