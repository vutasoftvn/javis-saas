-- BASELINE CANDIDATE (isolated verification only, NOT a production migration path)
-- Domain: services/company -- commercial + finance-legal + operations (verbatim from existing .up.sql, correct numeric order)
-- identity domain is NOT included here -- see company_identity_baseline_v1.sql (reconciled, chain was broken)

-- source: services/company/commercial/migrations/1_create_accounts_contacts.up.sql
CREATE SCHEMA IF NOT EXISTS sales;

CREATE TABLE sales.accounts (
  id BIGSERIAL PRIMARY KEY,
  workspace_id BIGINT NOT NULL,
  name TEXT NOT NULL,
  domain TEXT,
  industry TEXT,
  size_segment TEXT,
  country TEXT,
  source TEXT,
  lifecycle_status TEXT NOT NULL DEFAULT 'TARGET',
  owner_id BIGINT,
  tags JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  deleted_at TIMESTAMPTZ
);

CREATE UNIQUE INDEX uq_accounts_workspace_domain ON sales.accounts(workspace_id, domain) WHERE domain IS NOT NULL;
CREATE INDEX idx_accounts_workspace_id ON sales.accounts(workspace_id);

CREATE TABLE sales.contacts (
  id BIGSERIAL PRIMARY KEY,
  workspace_id BIGINT NOT NULL,
  account_id BIGINT REFERENCES sales.accounts(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  title TEXT,
  phone TEXT,
  email TEXT,
  source TEXT,
  consent_status TEXT,
  do_not_contact BOOLEAN NOT NULL DEFAULT false,
  owner_id BIGINT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  deleted_at TIMESTAMPTZ
);

CREATE UNIQUE INDEX uq_contacts_workspace_email ON sales.contacts(workspace_id, email) WHERE email IS NOT NULL;
CREATE INDEX idx_contacts_workspace_id ON sales.contacts(workspace_id);
CREATE INDEX idx_contacts_account_id ON sales.contacts(account_id);

-- source: services/company/commercial/migrations/2_create_sales_leads.up.sql
CREATE TABLE sales.sales_leads (
  id BIGSERIAL PRIMARY KEY,
  workspace_id BIGINT NOT NULL,
  key_result_id BIGINT,
  account_id BIGINT REFERENCES sales.accounts(id) ON DELETE SET NULL,
  contact_id BIGINT REFERENCES sales.contacts(id) ON DELETE SET NULL,
  name TEXT NOT NULL,
  company TEXT,
  stage TEXT NOT NULL DEFAULT 'NEW',
  value DOUBLE PRECISION,
  source TEXT,
  source_campaign_id BIGINT,
  source_experiment_id BIGINT,
  utm_source TEXT,
  utm_medium TEXT,
  utm_campaign TEXT,
  utm_content TEXT,
  utm_term TEXT,
  fit_score DOUBLE PRECISION,
  intent_score DOUBLE PRECISION,
  engagement_score DOUBLE PRECISION,
  qualification_status TEXT,
  disqualification_reason TEXT,
  next_action_at TIMESTAMPTZ,
  next_action_type TEXT,
  owner_id BIGINT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  deleted_at TIMESTAMPTZ
);

CREATE INDEX idx_sales_leads_workspace_id ON sales.sales_leads(workspace_id);
CREATE INDEX idx_sales_leads_key_result_id ON sales.sales_leads(key_result_id);
CREATE INDEX idx_sales_leads_account_id ON sales.sales_leads(account_id);
CREATE INDEX idx_sales_leads_contact_id ON sales.sales_leads(contact_id);

-- source: services/company/commercial/migrations/3_create_opportunities_customers.up.sql
CREATE TABLE sales.sales_opportunities (
  id BIGSERIAL PRIMARY KEY,
  workspace_id BIGINT NOT NULL,
  cycle_id BIGINT,
  account_id BIGINT NOT NULL REFERENCES sales.accounts(id) ON DELETE CASCADE,
  primary_contact_id BIGINT REFERENCES sales.contacts(id) ON DELETE SET NULL,
  owner_id BIGINT,
  source_lead_id BIGINT REFERENCES sales.sales_leads(id) ON DELETE SET NULL,
  product TEXT,
  stage TEXT NOT NULL DEFAULT 'DISCOVERY',
  estimated_value DOUBLE PRECISION,
  currency TEXT NOT NULL DEFAULT 'VND',
  probability DOUBLE PRECISION,
  expected_close_date DATE,
  pain_points JSONB,
  needs JSONB,
  objections JSONB,
  competitors JSONB,
  next_action TEXT,
  next_action_due_at TIMESTAMPTZ,
  won_reason TEXT,
  lost_reason TEXT,
  lost_reason_detail TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  deleted_at TIMESTAMPTZ
);

CREATE INDEX idx_opportunities_workspace_id ON sales.sales_opportunities(workspace_id);
CREATE INDEX idx_opportunities_account_id ON sales.sales_opportunities(account_id);

CREATE TABLE sales.customers (
  id BIGSERIAL PRIMARY KEY,
  workspace_id BIGINT NOT NULL,
  account_id BIGINT NOT NULL REFERENCES sales.accounts(id) ON DELETE CASCADE,
  acquired_from_opportunity_id BIGINT REFERENCES sales.sales_opportunities(id) ON DELETE SET NULL,
  lifecycle_status TEXT NOT NULL DEFAULT 'ONBOARDING',
  activation_status TEXT,
  owner_id BIGINT,
  first_purchase_at TIMESTAMPTZ,
  renewal_date DATE,
  health_status TEXT NOT NULL DEFAULT 'HEALTHY',
  last_success_interaction_at TIMESTAMPTZ,
  next_success_action_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  deleted_at TIMESTAMPTZ,
  UNIQUE (workspace_id, account_id)
);

CREATE INDEX idx_customers_workspace_id ON sales.customers(workspace_id);

-- source: services/company/commercial/migrations/4_create_marketing_domain.up.sql
CREATE SCHEMA IF NOT EXISTS commercial;

CREATE TABLE commercial.marketing_contexts (
    id BIGSERIAL PRIMARY KEY,
    workspace_id BIGINT NOT NULL,
    category VARCHAR(255),
    market JSONB,
    positioning JSONB,
    pricing JSONB,
    channels JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

CREATE INDEX idx_marketing_contexts_workspace ON commercial.marketing_contexts(workspace_id);

CREATE TABLE commercial.marketing_campaigns (
    id BIGSERIAL PRIMARY KEY,
    workspace_id BIGINT NOT NULL,
    name VARCHAR(255) NOT NULL,
    funnel_stage VARCHAR(50) NOT NULL DEFAULT 'discover',
    channels JSONB,
    budget DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    status VARCHAR(50) NOT NULL DEFAULT 'draft',
    start_date TIMESTAMPTZ,
    end_date TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

CREATE INDEX idx_marketing_campaigns_workspace ON commercial.marketing_campaigns(workspace_id);

CREATE TABLE commercial.campaign_assets (
    id BIGSERIAL PRIMARY KEY,
    workspace_id BIGINT NOT NULL,
    campaign_id BIGINT NOT NULL REFERENCES commercial.marketing_campaigns(id) ON DELETE CASCADE,
    asset_type VARCHAR(50) NOT NULL,
    title VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'draft',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

CREATE INDEX idx_campaign_assets_workspace ON commercial.campaign_assets(workspace_id);
CREATE INDEX idx_campaign_assets_campaign ON commercial.campaign_assets(campaign_id);

CREATE TABLE commercial.marketing_forms (
    id BIGSERIAL PRIMARY KEY,
    workspace_id BIGINT NOT NULL,
    title VARCHAR(255) NOT NULL,
    slug VARCHAR(255) NOT NULL,
    fields_schema JSONB NOT NULL DEFAULT '[]',
    is_published BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ,
    CONSTRAINT uix_marketing_forms_slug UNIQUE (workspace_id, slug)
);

CREATE INDEX idx_marketing_forms_workspace ON commercial.marketing_forms(workspace_id);

CREATE TABLE commercial.marketing_lead_intakes (
    id BIGSERIAL PRIMARY KEY,
    workspace_id BIGINT NOT NULL,
    form_id BIGINT REFERENCES commercial.marketing_forms(id) ON DELETE SET NULL,
    contact_data JSONB NOT NULL DEFAULT '{}',
    source VARCHAR(100),
    status VARCHAR(50) NOT NULL DEFAULT 'new',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

CREATE INDEX idx_marketing_lead_intakes_workspace ON commercial.marketing_lead_intakes(workspace_id);

-- source: services/company/commercial/migrations/5_create_billing_domain.up.sql
CREATE SCHEMA IF NOT EXISTS commercial;

CREATE TABLE commercial.invoices (
    id BIGSERIAL PRIMARY KEY,
    workspace_id BIGINT NOT NULL,
    customer_id BIGINT REFERENCES sales.customers(id) ON DELETE SET NULL,
    invoice_number VARCHAR(100) NOT NULL,
    amount DOUBLE PRECISION NOT NULL,
    currency VARCHAR(10) NOT NULL DEFAULT 'VND',
    status VARCHAR(50) NOT NULL DEFAULT 'draft',
    due_date TIMESTAMPTZ,
    paid_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ,
    CONSTRAINT uix_invoices_workspace_number UNIQUE (workspace_id, invoice_number)
);

CREATE INDEX idx_invoices_workspace ON commercial.invoices(workspace_id);

CREATE TABLE commercial.subscriptions (
    id BIGSERIAL PRIMARY KEY,
    workspace_id BIGINT NOT NULL,
    customer_id BIGINT REFERENCES sales.customers(id) ON DELETE SET NULL,
    plan_name VARCHAR(100) NOT NULL,
    billing_cycle VARCHAR(50) NOT NULL DEFAULT 'monthly',
    price DOUBLE PRECISION NOT NULL,
    currency VARCHAR(10) NOT NULL DEFAULT 'VND',
    status VARCHAR(50) NOT NULL DEFAULT 'active',
    current_period_start TIMESTAMPTZ,
    current_period_end TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

CREATE INDEX idx_subscriptions_workspace ON commercial.subscriptions(workspace_id);

-- source: services/company/commercial/migrations/6_add_idempotency_keys.up.sql
-- A retried agent write must not create a duplicate CRM record (blueprint
-- §82). Nullable so existing/plain writes are unaffected; multiple NULLs
-- don't conflict on the unique constraint.
ALTER TABLE sales.accounts ADD COLUMN idempotency_key TEXT;
ALTER TABLE sales.accounts ADD CONSTRAINT accounts_workspace_idempotency_key UNIQUE (workspace_id, idempotency_key);

ALTER TABLE sales.contacts ADD COLUMN idempotency_key TEXT;
ALTER TABLE sales.contacts ADD CONSTRAINT contacts_workspace_idempotency_key UNIQUE (workspace_id, idempotency_key);

ALTER TABLE sales.sales_leads ADD COLUMN idempotency_key TEXT;
ALTER TABLE sales.sales_leads ADD CONSTRAINT sales_leads_workspace_idempotency_key UNIQUE (workspace_id, idempotency_key);

ALTER TABLE sales.sales_opportunities ADD COLUMN idempotency_key TEXT;
ALTER TABLE sales.sales_opportunities ADD CONSTRAINT sales_opportunities_workspace_idempotency_key UNIQUE (workspace_id, idempotency_key);

-- source: services/company/commercial/migrations/7_snowflake_ids.up.sql
-- Migrate commercial and sales tables to Snowflake IDs
-- Truncate all data and drop auto-increment defaults
TRUNCATE TABLE commercial.campaign_assets, commercial.invoices, commercial.marketing_campaigns, commercial.marketing_contexts, commercial.marketing_forms, commercial.marketing_lead_intakes, commercial.subscriptions, sales.accounts, sales.contacts, sales.customers, sales.sales_leads, sales.sales_opportunities CASCADE;

ALTER TABLE commercial.campaign_assets ALTER COLUMN id DROP DEFAULT;
ALTER TABLE commercial.invoices ALTER COLUMN id DROP DEFAULT;
ALTER TABLE commercial.marketing_campaigns ALTER COLUMN id DROP DEFAULT;
ALTER TABLE commercial.marketing_contexts ALTER COLUMN id DROP DEFAULT;
ALTER TABLE commercial.marketing_forms ALTER COLUMN id DROP DEFAULT;
ALTER TABLE commercial.marketing_lead_intakes ALTER COLUMN id DROP DEFAULT;
ALTER TABLE commercial.subscriptions ALTER COLUMN id DROP DEFAULT;
ALTER TABLE sales.accounts ALTER COLUMN id DROP DEFAULT;
ALTER TABLE sales.contacts ALTER COLUMN id DROP DEFAULT;
ALTER TABLE sales.customers ALTER COLUMN id DROP DEFAULT;
ALTER TABLE sales.sales_leads ALTER COLUMN id DROP DEFAULT;
ALTER TABLE sales.sales_opportunities ALTER COLUMN id DROP DEFAULT;

-- source: services/company/commercial/migrations/8_actor_naming_standardization.up.sql
-- services/company/commercial/migrations/8_actor_naming_standardization.up.sql

-- Đồng bộ với operations/migrations/12: canonical actor field name là
-- *_member_id trên toàn bộ business schema.
ALTER TABLE sales.accounts RENAME COLUMN owner_id TO owner_member_id;
ALTER TABLE sales.contacts RENAME COLUMN owner_id TO owner_member_id;
ALTER TABLE sales.sales_leads RENAME COLUMN owner_id TO owner_member_id;
ALTER TABLE sales.sales_opportunities RENAME COLUMN owner_id TO owner_member_id;
ALTER TABLE sales.customers RENAME COLUMN owner_id TO owner_member_id;

-- source: services/company/finance-legal/migrations/1_create_accounting_profile_period.up.sql
CREATE SCHEMA IF NOT EXISTS finance;

CREATE TABLE finance.accounting_profiles (
  id BIGSERIAL PRIMARY KEY,
  workspace_id BIGINT NOT NULL,
  mode TEXT NOT NULL DEFAULT 'TT58_MODE_1',
  status TEXT NOT NULL DEFAULT 'DRAFT',
  confirmed_by BIGINT,
  confirmed_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  deleted_at TIMESTAMPTZ,
  UNIQUE (workspace_id)
);

CREATE TABLE finance.accounting_periods (
  id BIGSERIAL PRIMARY KEY,
  workspace_id BIGINT NOT NULL,
  start_date DATE NOT NULL,
  end_date DATE NOT NULL,
  status TEXT NOT NULL DEFAULT 'OPEN',
  closed_by BIGINT,
  closed_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  deleted_at TIMESTAMPTZ
);

CREATE INDEX idx_accounting_periods_workspace_id ON finance.accounting_periods(workspace_id);

-- source: services/company/finance-legal/migrations/2_create_transactions_exceptions.up.sql
CREATE TABLE finance.financial_transactions (
  id BIGSERIAL PRIMARY KEY,
  workspace_id BIGINT NOT NULL,
  document_id BIGINT,
  project_id BIGINT,
  cycle_id BIGINT,
  work_item_id BIGINT,
  transaction_date DATE NOT NULL,
  description TEXT NOT NULL,
  amount NUMERIC(20, 2) NOT NULL,
  direction TEXT NOT NULL,
  category TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  deleted_at TIMESTAMPTZ
);

CREATE INDEX idx_financial_transactions_workspace_id ON finance.financial_transactions(workspace_id);

CREATE TABLE finance.finance_exceptions (
  id BIGSERIAL PRIMARY KEY,
  workspace_id BIGINT NOT NULL,
  transaction_id BIGINT REFERENCES finance.financial_transactions(id) ON DELETE CASCADE,
  exception_type TEXT NOT NULL,
  severity TEXT NOT NULL DEFAULT 'WARNING',
  details JSONB,
  status TEXT NOT NULL DEFAULT 'OPEN',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  deleted_at TIMESTAMPTZ
);

CREATE INDEX idx_finance_exceptions_workspace_id ON finance.finance_exceptions(workspace_id);
CREATE INDEX idx_finance_exceptions_transaction_id ON finance.finance_exceptions(transaction_id);

-- source: services/company/finance-legal/migrations/3_create_finance_snapshots.up.sql
CREATE TABLE finance.finance_management_snapshots (
  id BIGSERIAL PRIMARY KEY,
  workspace_id BIGINT NOT NULL,
  cycle_id BIGINT,
  as_of DATE NOT NULL,
  cash NUMERIC(20, 2) NOT NULL,
  burn NUMERIC(20, 2) NOT NULL,
  runway_months NUMERIC(12, 2),
  revenue NUMERIC(20, 2) NOT NULL DEFAULT 0,
  expenses NUMERIC(20, 2) NOT NULL DEFAULT 0,
  budget_variance NUMERIC(20, 2),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  deleted_at TIMESTAMPTZ
);

CREATE INDEX idx_finance_snapshots_workspace_id ON finance.finance_management_snapshots(workspace_id);
CREATE INDEX idx_finance_snapshots_workspace_as_of ON finance.finance_management_snapshots(workspace_id, as_of DESC);

-- source: services/company/finance-legal/migrations/4_create_legal.up.sql
CREATE SCHEMA IF NOT EXISTS legal;

CREATE TABLE legal.legal_checklist_items (
  id BIGSERIAL PRIMARY KEY,
  workspace_id BIGINT NOT NULL,
  title TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'OPEN',
  evidence_artifact_id BIGINT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  deleted_at TIMESTAMPTZ
);

CREATE INDEX idx_legal_checklist_items_workspace_id ON legal.legal_checklist_items(workspace_id);

CREATE TABLE legal.legal_obligations (
  id BIGSERIAL PRIMARY KEY,
  workspace_id BIGINT NOT NULL,
  title TEXT NOT NULL,
  description TEXT,
  due_at TIMESTAMPTZ,
  status TEXT NOT NULL DEFAULT 'OPEN',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  deleted_at TIMESTAMPTZ
);

CREATE INDEX idx_legal_obligations_workspace_id ON legal.legal_obligations(workspace_id);

-- source: services/company/finance-legal/migrations/5_create_accounting_regime_vn.up.sql
CREATE TABLE finance.accounting_fiscal_profiles (
    id BIGSERIAL PRIMARY KEY,
    workspace_id BIGINT NOT NULL,
    fiscal_year INT NOT NULL,
    regulation_code VARCHAR(50) NOT NULL DEFAULT 'TT58_2026',
    mode VARCHAR(50) NOT NULL DEFAULT 'TT58_MODE_1',
    status VARCHAR(30) NOT NULL DEFAULT 'ACTIVE',
    locked_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ,
    CONSTRAINT uix_fiscal_profile_workspace_year UNIQUE (workspace_id, fiscal_year)
);

CREATE INDEX idx_fiscal_profiles_workspace ON finance.accounting_fiscal_profiles(workspace_id);

CREATE TABLE finance.accounting_coa_mappings (
    id BIGSERIAL PRIMARY KEY,
    source_regulation VARCHAR(50) NOT NULL,
    target_regulation VARCHAR(50) NOT NULL,
    source_account_code VARCHAR(50) NOT NULL,
    target_account_code VARCHAR(50) NOT NULL,
    mapping_type VARCHAR(30) NOT NULL DEFAULT 'DIRECT_1_1',
    description VARCHAR(255)
);

CREATE INDEX idx_coa_mappings_source ON finance.accounting_coa_mappings(source_regulation, source_account_code);
CREATE INDEX idx_coa_mappings_target ON finance.accounting_coa_mappings(target_regulation, target_account_code);

CREATE TABLE finance.accounting_regime_transition_logs (
    id BIGSERIAL PRIMARY KEY,
    workspace_id BIGINT NOT NULL,
    from_fiscal_year INT NOT NULL,
    to_fiscal_year INT NOT NULL,
    from_regulation VARCHAR(50) NOT NULL,
    to_regulation VARCHAR(50) NOT NULL,
    cutoff_date DATE NOT NULL,
    is_balanced BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

CREATE INDEX idx_regime_transition_workspace ON finance.accounting_regime_transition_logs(workspace_id);

-- source: services/company/finance-legal/migrations/6_create_validation_domain.up.sql
CREATE SCHEMA IF NOT EXISTS validation;

CREATE TABLE validation.validation_hypotheses (
    id BIGSERIAL PRIMARY KEY,
    workspace_id BIGINT NOT NULL,
    project_id BIGINT,
    title VARCHAR(255) NOT NULL,
    statement TEXT NOT NULL,
    confidence_score DOUBLE PRECISION NOT NULL DEFAULT 0.5,
    status VARCHAR(50) NOT NULL DEFAULT 'TESTING',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

CREATE INDEX idx_hypotheses_workspace ON validation.validation_hypotheses(workspace_id);

CREATE TABLE validation.validation_experiments (
    id BIGSERIAL PRIMARY KEY,
    workspace_id BIGINT NOT NULL,
    hypothesis_id BIGINT NOT NULL REFERENCES validation.validation_hypotheses(id) ON DELETE CASCADE,
    experiment_type VARCHAR(50) NOT NULL DEFAULT 'INTERVIEW',
    title VARCHAR(255) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'RUNNING',
    start_date TIMESTAMPTZ,
    end_date TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

CREATE INDEX idx_experiments_workspace ON validation.validation_experiments(workspace_id);
CREATE INDEX idx_experiments_hypothesis ON validation.validation_experiments(hypothesis_id);

CREATE TABLE validation.evidence_items (
    id BIGSERIAL PRIMARY KEY,
    workspace_id BIGINT NOT NULL,
    experiment_id BIGINT NOT NULL REFERENCES validation.validation_experiments(id) ON DELETE CASCADE,
    evidence_type VARCHAR(50) NOT NULL DEFAULT 'QUOTE',
    title VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    strength_score DOUBLE PRECISION NOT NULL DEFAULT 1.0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

CREATE INDEX idx_evidence_workspace ON validation.evidence_items(workspace_id);
CREATE INDEX idx_evidence_experiment ON validation.evidence_items(experiment_id);

CREATE TABLE validation.customer_interviews (
    id BIGSERIAL PRIMARY KEY,
    workspace_id BIGINT NOT NULL,
    customer_name VARCHAR(255) NOT NULL,
    interview_date TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    key_insights TEXT,
    pain_points TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

CREATE INDEX idx_customer_interviews_workspace ON validation.customer_interviews(workspace_id);

-- source: services/company/finance-legal/migrations/7_add_transaction_idempotency_key.up.sql
-- A retried financial-transaction write must not create a duplicate charge
-- (blueprint §82 — business writes need an idempotency key). Nullable so
-- existing/plain writes are unaffected; multiple NULLs don't conflict.
ALTER TABLE finance.financial_transactions ADD COLUMN idempotency_key TEXT;
ALTER TABLE finance.financial_transactions ADD CONSTRAINT financial_transactions_workspace_idempotency_key
  UNIQUE (workspace_id, idempotency_key);

-- source: services/company/finance-legal/migrations/8_add_more_idempotency_keys.up.sql
-- Same reasoning as 7_add_transaction_idempotency_key.up.sql, extended to
-- the other agent-writable finance/legal tables (blueprint §82).
ALTER TABLE finance.accounting_periods ADD COLUMN idempotency_key TEXT;
ALTER TABLE finance.accounting_periods ADD CONSTRAINT accounting_periods_workspace_idempotency_key UNIQUE (workspace_id, idempotency_key);

ALTER TABLE legal.legal_obligations ADD COLUMN idempotency_key TEXT;
ALTER TABLE legal.legal_obligations ADD CONSTRAINT legal_obligations_workspace_idempotency_key UNIQUE (workspace_id, idempotency_key);

ALTER TABLE legal.legal_checklist_items ADD COLUMN idempotency_key TEXT;
ALTER TABLE legal.legal_checklist_items ADD CONSTRAINT legal_checklist_items_workspace_idempotency_key UNIQUE (workspace_id, idempotency_key);

-- source: services/company/finance-legal/migrations/9_add_transaction_approval.up.sql
-- Approval gate cho giao dịch tài chính vượt ngưỡng rủi ro cao (CLAUDE.md §11:
-- high-risk actions phải qua permission/approval bằng deterministic code,
-- không chỉ dựa vào PolicyEngine/ApprovalService phía agentos vì endpoint
-- này có thể bị gọi trực tiếp, né qua tầng agent orchestrator).
ALTER TABLE finance.financial_transactions
  ADD COLUMN approval_status TEXT NOT NULL DEFAULT 'AUTO_APPROVED',
  ADD COLUMN approved_by_user_id BIGINT,
  ADD COLUMN approved_at TIMESTAMPTZ;

-- source: services/company/finance-legal/migrations/10_snowflake_ids.up.sql
-- Migrate finance-legal module from bigserial to Snowflake IDs
-- All affected tables are truncated first to safely remove default values

TRUNCATE TABLE finance.accounting_coa_mappings, finance.accounting_fiscal_profiles, finance.accounting_periods, finance.accounting_profiles, finance.accounting_regime_transition_logs, finance.finance_exceptions, finance.finance_management_snapshots, finance.financial_transactions, legal.legal_checklist_items, legal.legal_obligations, validation.customer_interviews, validation.evidence_items, validation.validation_experiments, validation.validation_hypotheses CASCADE;

ALTER TABLE finance.accounting_coa_mappings ALTER COLUMN id DROP DEFAULT;
ALTER TABLE finance.accounting_fiscal_profiles ALTER COLUMN id DROP DEFAULT;
ALTER TABLE finance.accounting_periods ALTER COLUMN id DROP DEFAULT;
ALTER TABLE finance.accounting_profiles ALTER COLUMN id DROP DEFAULT;
ALTER TABLE finance.accounting_regime_transition_logs ALTER COLUMN id DROP DEFAULT;
ALTER TABLE finance.finance_exceptions ALTER COLUMN id DROP DEFAULT;
ALTER TABLE finance.finance_management_snapshots ALTER COLUMN id DROP DEFAULT;
ALTER TABLE finance.financial_transactions ALTER COLUMN id DROP DEFAULT;
ALTER TABLE legal.legal_checklist_items ALTER COLUMN id DROP DEFAULT;
ALTER TABLE legal.legal_obligations ALTER COLUMN id DROP DEFAULT;
ALTER TABLE validation.customer_interviews ALTER COLUMN id DROP DEFAULT;
ALTER TABLE validation.evidence_items ALTER COLUMN id DROP DEFAULT;
ALTER TABLE validation.validation_experiments ALTER COLUMN id DROP DEFAULT;
ALTER TABLE validation.validation_hypotheses ALTER COLUMN id DROP DEFAULT;

-- source: services/company/finance-legal/migrations/11_drop_validation_domain.up.sql
-- services/company/finance-legal/migrations/11_drop_validation_domain.up.sql

-- finance-legal.validation subsystem (validation_hypotheses/validation_experiments/
-- evidence_items/customer_interviews) không có consumer thật ngoài chính test của nó —
-- operations/strategy (assumption -> experiment -> evidence -> gate -> decision) mới là
-- chain canonical. Xem docs/superpowers/specs/2026-08-23-identity-foundation-plan-a-design.md
-- mục "Plan B — Company Business Schema Cleanup" điểm 1.
DROP TABLE IF EXISTS validation.evidence_items;
DROP TABLE IF EXISTS validation.validation_experiments;
DROP TABLE IF EXISTS validation.customer_interviews;
DROP TABLE IF EXISTS validation.validation_hypotheses;
DROP SCHEMA IF EXISTS validation;

-- source: services/company/operations/migrations/1_create_tasks.up.sql
CREATE SCHEMA IF NOT EXISTS operating;

CREATE TABLE operating.tasks (
  id BIGSERIAL PRIMARY KEY,
  workspace_id BIGINT NOT NULL,
  title TEXT NOT NULL,
  idempotency_key TEXT,
  status TEXT NOT NULL DEFAULT 'todo',
  priority TEXT NOT NULL DEFAULT 'medium',
  planned_start_at TIMESTAMPTZ,
  due_at TIMESTAMPTZ,
  timezone TEXT NOT NULL DEFAULT 'UTC',
  assignee_id BIGINT,
  source TEXT,
  completion_policy TEXT,
  initiative_id BIGINT,
  weekly_commitment_id BIGINT,
  sort_key DOUBLE PRECISION,
  assignee_member_id BIGINT,
  owner_member_id BIGINT,
  execution_mode TEXT,
  function TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  deleted_at TIMESTAMPTZ,
  UNIQUE (workspace_id, idempotency_key)
);

CREATE INDEX idx_tasks_workspace_id ON operating.tasks(workspace_id);
CREATE INDEX idx_tasks_function ON operating.tasks(function);

-- source: services/company/operations/migrations/2_create_initiatives.up.sql
CREATE SCHEMA IF NOT EXISTS strategy;

CREATE TABLE strategy.initiatives (
  id BIGSERIAL PRIMARY KEY,
  workspace_id BIGINT NOT NULL,
  brain_id BIGINT,
  project_id BIGINT,
  offering_id BIGINT,
  title TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'active',
  owner_id BIGINT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  deleted_at TIMESTAMPTZ
);

CREATE INDEX idx_initiatives_workspace_id ON strategy.initiatives(workspace_id);

ALTER TABLE operating.tasks
  ADD CONSTRAINT fk_tasks_initiative_id FOREIGN KEY (initiative_id) REFERENCES strategy.initiatives(id) ON DELETE SET NULL;

-- source: services/company/operations/migrations/3_create_okr.up.sql
CREATE TABLE strategy.okr_cycles (
  id BIGSERIAL PRIMARY KEY,
  workspace_id BIGINT NOT NULL,
  brain_id BIGINT,
  mvp_stage_id BIGINT,
  name TEXT NOT NULL,
  start_date TIMESTAMPTZ,
  end_date TIMESTAMPTZ,
  status TEXT NOT NULL DEFAULT 'draft',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  deleted_at TIMESTAMPTZ
);

CREATE TABLE strategy.okr_objectives (
  id BIGSERIAL PRIMARY KEY,
  workspace_id BIGINT NOT NULL,
  cycle_id BIGINT NOT NULL REFERENCES strategy.okr_cycles(id) ON DELETE CASCADE,
  strategic_objective_id BIGINT,
  title TEXT NOT NULL,
  why TEXT,
  owner_id BIGINT,
  status TEXT NOT NULL DEFAULT 'draft',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  deleted_at TIMESTAMPTZ
);

CREATE TABLE strategy.key_results (
  id BIGSERIAL PRIMARY KEY,
  workspace_id BIGINT NOT NULL,
  objective_id BIGINT NOT NULL REFERENCES strategy.okr_objectives(id) ON DELETE CASCADE,
  title TEXT,
  metric_id BIGINT,
  baseline_value DOUBLE PRECISION,
  current_value DOUBLE PRECISION,
  target_value DOUBLE PRECISION,
  unit TEXT,
  cadence TEXT,
  metric_type TEXT,
  evidence_refs JSONB,
  status TEXT NOT NULL DEFAULT 'draft',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  deleted_at TIMESTAMPTZ
);

CREATE INDEX idx_okr_cycles_workspace_id ON strategy.okr_cycles(workspace_id);
CREATE INDEX idx_okr_objectives_workspace_id ON strategy.okr_objectives(workspace_id);
CREATE INDEX idx_okr_objectives_cycle_id ON strategy.okr_objectives(cycle_id);
CREATE INDEX idx_key_results_workspace_id ON strategy.key_results(workspace_id);
CREATE INDEX idx_key_results_objective_id ON strategy.key_results(objective_id);

-- source: services/company/operations/migrations/4_create_task_extensions.up.sql
CREATE TABLE operating.task_dependencies (
    id BIGSERIAL PRIMARY KEY,
    task_id BIGINT NOT NULL REFERENCES operating.tasks(id) ON DELETE CASCADE,
    depends_on_task_id BIGINT NOT NULL REFERENCES operating.tasks(id) ON DELETE CASCADE,
    dependency_type VARCHAR(50) DEFAULT 'BLOCKS',
    status VARCHAR(50) NOT NULL DEFAULT 'PENDING',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

CREATE INDEX idx_task_dependencies_task_id ON operating.task_dependencies(task_id);
CREATE INDEX idx_task_dependencies_depends_on ON operating.task_dependencies(depends_on_task_id);

CREATE TABLE operating.task_schedules (
    id BIGSERIAL PRIMARY KEY,
    task_id BIGINT NOT NULL REFERENCES operating.tasks(id) ON DELETE CASCADE,
    schedule_type VARCHAR(50) NOT NULL DEFAULT 'once',
    cron_expr VARCHAR(100),
    next_run_at TIMESTAMPTZ,
    active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

CREATE INDEX idx_task_schedules_task_id ON operating.task_schedules(task_id);

-- source: services/company/operations/migrations/5_create_twelve_week_year.up.sql
CREATE TABLE operating.twelve_week_cycles (
    id BIGSERIAL PRIMARY KEY,
    workspace_id BIGINT NOT NULL,
    brain_id BIGINT,
    project_id BIGINT,
    theme VARCHAR(255),
    vision_statement TEXT NOT NULL DEFAULT '',
    stage_at_start VARCHAR(50) NOT NULL DEFAULT 'S1_PROBLEM_VALIDATION',
    current_week INT NOT NULL DEFAULT 1,
    duration_weeks INT NOT NULL DEFAULT 12,
    overall_execution_score DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    start_date TIMESTAMPTZ,
    end_date TIMESTAMPTZ,
    commitment_level VARCHAR(50),
    status VARCHAR(50) NOT NULL DEFAULT 'ACTIVE',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

CREATE INDEX idx_twelve_week_cycles_workspace ON operating.twelve_week_cycles(workspace_id);

CREATE TABLE operating.weekly_plans (
    id BIGSERIAL PRIMARY KEY,
    workspace_id BIGINT NOT NULL,
    cycle_id BIGINT NOT NULL REFERENCES operating.twelve_week_cycles(id) ON DELETE CASCADE,
    week_no INT NOT NULL,
    start_date TIMESTAMPTZ,
    end_date TIMESTAMPTZ,
    focus TEXT,
    mission TEXT,
    execution_score DOUBLE PRECISION,
    outcome_score DOUBLE PRECISION,
    reflection TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ,
    CONSTRAINT uix_weekly_plan_cycle_week UNIQUE (cycle_id, week_no)
);

CREATE INDEX idx_weekly_plans_workspace ON operating.weekly_plans(workspace_id);
CREATE INDEX idx_weekly_plans_cycle ON operating.weekly_plans(cycle_id);

CREATE TABLE operating.weekly_commitments (
    id BIGSERIAL PRIMARY KEY,
    workspace_id BIGINT NOT NULL,
    weekly_plan_id BIGINT NOT NULL REFERENCES operating.weekly_plans(id) ON DELETE CASCADE,
    initiative_id BIGINT REFERENCES strategy.initiatives(id) ON DELETE SET NULL,
    title VARCHAR(255) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'todo',
    planned_effort VARCHAR(50),
    commitment_owner_type VARCHAR(50) DEFAULT 'FOUNDER',
    execution_mode VARCHAR(50) DEFAULT 'MANUAL',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

CREATE INDEX idx_weekly_commitments_workspace ON operating.weekly_commitments(workspace_id);
CREATE INDEX idx_weekly_commitments_plan ON operating.weekly_commitments(weekly_plan_id);

-- source: services/company/operations/migrations/6_create_projects_portfolios.up.sql
CREATE TABLE strategy.portfolios (
    id BIGSERIAL PRIMARY KEY,
    workspace_id BIGINT NOT NULL,
    brain_id BIGINT,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    strategic_focus VARCHAR(255),
    status VARCHAR(50) NOT NULL DEFAULT 'active',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

CREATE INDEX idx_portfolios_workspace ON strategy.portfolios(workspace_id);

CREATE TABLE strategy.projects (
    id BIGSERIAL PRIMARY KEY,
    workspace_id BIGINT NOT NULL,
    brain_id BIGINT,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    phase VARCHAR(50),
    current_gate VARCHAR(50),
    status VARCHAR(50) NOT NULL DEFAULT 'active',
    owner_id BIGINT,
    project_type VARCHAR(50),
    strategic_priority VARCHAR(50),
    founder_attention_budget DOUBLE PRECISION,
    portfolio_id BIGINT REFERENCES strategy.portfolios(id) ON DELETE SET NULL,
    start_date TIMESTAMPTZ,
    end_date TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

CREATE INDEX idx_projects_workspace ON strategy.projects(workspace_id);
CREATE INDEX idx_projects_portfolio ON strategy.projects(portfolio_id);

CREATE TABLE strategy.portfolio_projects (
    id BIGSERIAL PRIMARY KEY,
    workspace_id BIGINT NOT NULL,
    portfolio_id BIGINT NOT NULL REFERENCES strategy.portfolios(id) ON DELETE CASCADE,
    project_id BIGINT NOT NULL REFERENCES strategy.projects(id) ON DELETE CASCADE,
    strategic_priority VARCHAR(50) NOT NULL DEFAULT 'core',
    capacity_allocation DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    founder_attention_hours DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ,
    CONSTRAINT uix_portfolio_project UNIQUE (portfolio_id, project_id)
);

CREATE INDEX idx_portfolio_projects_portfolio ON strategy.portfolio_projects(portfolio_id);
CREATE INDEX idx_portfolio_projects_project ON strategy.portfolio_projects(project_id);

-- source: services/company/operations/migrations/7_create_strategy_domain.up.sql
-- Phase 2: Strategy & Startup Co-Founder Methodology Domain

CREATE TABLE IF NOT EXISTS strategy.stage_policies (
    id BIGSERIAL PRIMARY KEY,
    company_id BIGINT NOT NULL,
    workspace_id BIGINT NOT NULL,
    stage_key VARCHAR(50) NOT NULL,
    requirements JSONB NOT NULL DEFAULT '[]',
    minimum_evidence_score DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    blocking_risk_rules JSONB NOT NULL DEFAULT '[]',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

CREATE INDEX idx_stage_policies_company_workspace ON strategy.stage_policies(company_id, workspace_id);
CREATE INDEX idx_stage_policies_stage_key ON strategy.stage_policies(stage_key);

CREATE TABLE IF NOT EXISTS strategy.stage_transitions (
    id BIGSERIAL PRIMARY KEY,
    company_id BIGINT NOT NULL,
    workspace_id BIGINT NOT NULL,
    from_stage VARCHAR(50) NOT NULL,
    to_stage VARCHAR(50) NOT NULL,
    policy_id BIGINT REFERENCES strategy.stage_policies(id) ON DELETE SET NULL,
    allowed BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

CREATE INDEX idx_stage_transitions_company_workspace ON strategy.stage_transitions(company_id, workspace_id);

CREATE TABLE IF NOT EXISTS strategy.assumptions (
    id BIGSERIAL PRIMARY KEY,
    company_id BIGINT NOT NULL,
    workspace_id BIGINT NOT NULL,
    project_id BIGINT NOT NULL REFERENCES strategy.projects(id) ON DELETE CASCADE,
    statement TEXT NOT NULL,
    importance INTEGER NOT NULL DEFAULT 1,
    uncertainty INTEGER NOT NULL DEFAULT 1,
    risk_score DOUBLE PRECISION NOT NULL DEFAULT 1.0,
    status VARCHAR(50) NOT NULL DEFAULT 'untested',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

CREATE INDEX idx_assumptions_company_workspace ON strategy.assumptions(company_id, workspace_id);
CREATE INDEX idx_assumptions_project ON strategy.assumptions(project_id);

CREATE TABLE IF NOT EXISTS strategy.experiments (
    id BIGSERIAL PRIMARY KEY,
    company_id BIGINT NOT NULL,
    workspace_id BIGINT NOT NULL,
    project_id BIGINT NOT NULL REFERENCES strategy.projects(id) ON DELETE CASCADE,
    assumption_id BIGINT REFERENCES strategy.assumptions(id) ON DELETE SET NULL,
    hypothesis TEXT NOT NULL,
    method TEXT NOT NULL,
    success_criteria TEXT NOT NULL,
    budget DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    owner_workforce_member_id BIGINT,
    status VARCHAR(50) NOT NULL DEFAULT 'draft',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

CREATE INDEX idx_experiments_company_workspace ON strategy.experiments(company_id, workspace_id);
CREATE INDEX idx_experiments_project ON strategy.experiments(project_id);
CREATE INDEX idx_experiments_assumption ON strategy.experiments(assumption_id);

CREATE TABLE IF NOT EXISTS strategy.evidence (
    id BIGSERIAL PRIMARY KEY,
    company_id BIGINT NOT NULL,
    workspace_id BIGINT NOT NULL,
    experiment_id BIGINT REFERENCES strategy.experiments(id) ON DELETE SET NULL,
    project_id BIGINT NOT NULL REFERENCES strategy.projects(id) ON DELETE CASCADE,
    source_type VARCHAR(50) NOT NULL,
    claim TEXT NOT NULL,
    strength DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    confidence DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    supports_or_refutes VARCHAR(20) NOT NULL DEFAULT 'supports',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

CREATE INDEX idx_evidence_company_workspace ON strategy.evidence(company_id, workspace_id);
CREATE INDEX idx_evidence_project ON strategy.evidence(project_id);
CREATE INDEX idx_evidence_experiment ON strategy.evidence(experiment_id);

CREATE TABLE IF NOT EXISTS strategy.interviews (
    id BIGSERIAL PRIMARY KEY,
    company_id BIGINT NOT NULL,
    workspace_id BIGINT NOT NULL,
    project_id BIGINT NOT NULL REFERENCES strategy.projects(id) ON DELETE CASCADE,
    contact_ref BIGINT,
    notes TEXT NOT NULL,
    conducted_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

CREATE INDEX idx_interviews_company_workspace ON strategy.interviews(company_id, workspace_id);
CREATE INDEX idx_interviews_project ON strategy.interviews(project_id);

CREATE TABLE IF NOT EXISTS strategy.discovery_signals (
    id BIGSERIAL PRIMARY KEY,
    company_id BIGINT NOT NULL,
    workspace_id BIGINT NOT NULL,
    project_id BIGINT NOT NULL REFERENCES strategy.projects(id) ON DELETE CASCADE,
    signal_type VARCHAR(50) NOT NULL,
    payload JSONB NOT NULL DEFAULT '{}',
    source TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

CREATE INDEX idx_discovery_signals_company_workspace ON strategy.discovery_signals(company_id, workspace_id);
CREATE INDEX idx_discovery_signals_project ON strategy.discovery_signals(project_id);

CREATE TABLE IF NOT EXISTS strategy.gate_evaluations (
    id BIGSERIAL PRIMARY KEY,
    company_id BIGINT NOT NULL,
    workspace_id BIGINT NOT NULL,
    project_id BIGINT NOT NULL REFERENCES strategy.projects(id) ON DELETE CASCADE,
    stage_policy_id BIGINT REFERENCES strategy.stage_policies(id) ON DELETE SET NULL,
    requirements_met BOOLEAN NOT NULL DEFAULT FALSE,
    evidence_score DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    blocking_risks JSONB NOT NULL DEFAULT '[]',
    result VARCHAR(50) NOT NULL DEFAULT 'pending',
    rationale TEXT NOT NULL DEFAULT '',
    human_override BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

CREATE INDEX idx_gate_evaluations_company_workspace ON strategy.gate_evaluations(company_id, workspace_id);
CREATE INDEX idx_gate_evaluations_project ON strategy.gate_evaluations(project_id);

CREATE TABLE IF NOT EXISTS strategy.decision_records (
    id BIGSERIAL PRIMARY KEY,
    company_id BIGINT NOT NULL,
    workspace_id BIGINT NOT NULL,
    project_id BIGINT NOT NULL REFERENCES strategy.projects(id) ON DELETE CASCADE,
    gate_evaluation_id BIGINT REFERENCES strategy.gate_evaluations(id) ON DELETE SET NULL,
    decision VARCHAR(50) NOT NULL,
    actor_workforce_member_id BIGINT,
    evidence_snapshot JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

CREATE INDEX idx_decision_records_company_workspace ON strategy.decision_records(company_id, workspace_id);
CREATE INDEX idx_decision_records_project ON strategy.decision_records(project_id);

CREATE TABLE IF NOT EXISTS strategy.next_action_candidates (
    id BIGSERIAL PRIMARY KEY,
    company_id BIGINT NOT NULL,
    workspace_id BIGINT NOT NULL,
    project_id BIGINT NOT NULL REFERENCES strategy.projects(id) ON DELETE CASCADE,
    source VARCHAR(50) NOT NULL,
    score DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    rationale TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

CREATE INDEX idx_next_action_candidates_company_workspace ON strategy.next_action_candidates(company_id, workspace_id);
CREATE INDEX idx_next_action_candidates_project ON strategy.next_action_candidates(project_id);

CREATE TABLE IF NOT EXISTS strategy.next_action_rankings (
    id BIGSERIAL PRIMARY KEY,
    company_id BIGINT NOT NULL,
    workspace_id BIGINT NOT NULL,
    project_id BIGINT NOT NULL REFERENCES strategy.projects(id) ON DELETE CASCADE,
    candidate_id BIGINT NOT NULL REFERENCES strategy.next_action_candidates(id) ON DELETE CASCADE,
    rank INTEGER NOT NULL,
    llm_rerank_note TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

CREATE INDEX idx_next_action_rankings_company_workspace ON strategy.next_action_rankings(company_id, workspace_id);
CREATE INDEX idx_next_action_rankings_project ON strategy.next_action_rankings(project_id);

-- source: services/company/operations/migrations/8_snowflake_ids.up.sql
-- Migrate operations module (13 tables) from bigserial to Snowflake IDs
-- Truncate all tables to clear existing auto-increment data
TRUNCATE TABLE operating.task_dependencies, operating.task_schedules, operating.tasks, operating.twelve_week_cycles, operating.weekly_commitments, operating.weekly_plans, strategy.initiatives, strategy.okr_cycles, strategy.okr_objectives, strategy.key_results, strategy.portfolios, strategy.projects, strategy.portfolio_projects CASCADE;

-- Drop bigserial defaults for all ID columns
ALTER TABLE operating.task_dependencies ALTER COLUMN id DROP DEFAULT;
ALTER TABLE operating.task_schedules ALTER COLUMN id DROP DEFAULT;
ALTER TABLE operating.tasks ALTER COLUMN id DROP DEFAULT;
ALTER TABLE operating.twelve_week_cycles ALTER COLUMN id DROP DEFAULT;
ALTER TABLE operating.weekly_commitments ALTER COLUMN id DROP DEFAULT;
ALTER TABLE operating.weekly_plans ALTER COLUMN id DROP DEFAULT;
ALTER TABLE strategy.initiatives ALTER COLUMN id DROP DEFAULT;
ALTER TABLE strategy.okr_cycles ALTER COLUMN id DROP DEFAULT;
ALTER TABLE strategy.okr_objectives ALTER COLUMN id DROP DEFAULT;
ALTER TABLE strategy.key_results ALTER COLUMN id DROP DEFAULT;
ALTER TABLE strategy.portfolios ALTER COLUMN id DROP DEFAULT;
ALTER TABLE strategy.projects ALTER COLUMN id DROP DEFAULT;
ALTER TABLE strategy.portfolio_projects ALTER COLUMN id DROP DEFAULT;

-- source: services/company/operations/migrations/9_strategy_snowflake_ids.up.sql
-- Migrate strategy module to snowflake IDs
-- Remove bigserial defaults from all strategy tables

TRUNCATE TABLE strategy.assumptions, strategy.decision_records, strategy.discovery_signals, strategy.evidence, strategy.experiments, strategy.gate_evaluations, strategy.interviews, strategy.next_action_candidates, strategy.next_action_rankings, strategy.stage_policies, strategy.stage_transitions CASCADE;

ALTER TABLE strategy.assumptions ALTER COLUMN id DROP DEFAULT;
ALTER TABLE strategy.decision_records ALTER COLUMN id DROP DEFAULT;
ALTER TABLE strategy.discovery_signals ALTER COLUMN id DROP DEFAULT;
ALTER TABLE strategy.evidence ALTER COLUMN id DROP DEFAULT;
ALTER TABLE strategy.experiments ALTER COLUMN id DROP DEFAULT;
ALTER TABLE strategy.gate_evaluations ALTER COLUMN id DROP DEFAULT;
ALTER TABLE strategy.interviews ALTER COLUMN id DROP DEFAULT;
ALTER TABLE strategy.next_action_candidates ALTER COLUMN id DROP DEFAULT;
ALTER TABLE strategy.next_action_rankings ALTER COLUMN id DROP DEFAULT;
ALTER TABLE strategy.stage_policies ALTER COLUMN id DROP DEFAULT;
ALTER TABLE strategy.stage_transitions ALTER COLUMN id DROP DEFAULT;

-- source: services/company/operations/migrations/10_drop_ghost_fields.up.sql
-- services/company/operations/migrations/10_drop_ghost_fields.up.sql

-- brain_id/mvp_stage_id/offering_id là ghost field: không có bảng owner
-- (knowledge.brains, commercial.offerings không tồn tại), chỉ được set/đọc
-- xuyên suốt như DTO pass-through, không dùng trong bất kỳ query/filter nào.
-- Xem docs/superpowers/specs/2026-08-23-identity-foundation-plan-a-design.md
-- mục "Plan B" điểm 2.
ALTER TABLE strategy.initiatives DROP COLUMN IF EXISTS brain_id;
ALTER TABLE strategy.initiatives DROP COLUMN IF EXISTS offering_id;
ALTER TABLE strategy.okr_cycles DROP COLUMN IF EXISTS brain_id;
ALTER TABLE strategy.okr_cycles DROP COLUMN IF EXISTS mvp_stage_id;
ALTER TABLE operating.twelve_week_cycles DROP COLUMN IF EXISTS brain_id;
ALTER TABLE strategy.portfolios DROP COLUMN IF EXISTS brain_id;
ALTER TABLE strategy.projects DROP COLUMN IF EXISTS brain_id;

-- source: services/company/operations/migrations/11_dedupe_strategy_company_workspace_id.up.sql
-- services/company/operations/migrations/11_dedupe_strategy_company_workspace_id.up.sql

-- Canonical tenant key trong Company DB = workspace_id duy nhất.
-- core.workspaces.platform_company_id là nơi duy nhất giữ mapping sang
-- COSA companyId — business row không lưu song song company_id +
-- workspace_id nữa. Xem Plan B, nguyên tắc canonical tenant key.
ALTER TABLE strategy.stage_policies DROP COLUMN IF EXISTS company_id;
ALTER TABLE strategy.stage_transitions DROP COLUMN IF EXISTS company_id;
ALTER TABLE strategy.assumptions DROP COLUMN IF EXISTS company_id;
ALTER TABLE strategy.experiments DROP COLUMN IF EXISTS company_id;
ALTER TABLE strategy.evidence DROP COLUMN IF EXISTS company_id;
ALTER TABLE strategy.interviews DROP COLUMN IF EXISTS company_id;
ALTER TABLE strategy.discovery_signals DROP COLUMN IF EXISTS company_id;
ALTER TABLE strategy.gate_evaluations DROP COLUMN IF EXISTS company_id;
ALTER TABLE strategy.decision_records DROP COLUMN IF EXISTS company_id;
ALTER TABLE strategy.next_action_candidates DROP COLUMN IF EXISTS company_id;
ALTER TABLE strategy.next_action_rankings DROP COLUMN IF EXISTS company_id;

-- source: services/company/operations/migrations/12_actor_naming_standardization.up.sql
-- services/company/operations/migrations/12_actor_naming_standardization.up.sql

-- Canonical actor = workforce_members.id (có thể là human hoặc AI agent),
-- không dùng user_id cho business actor. Chuẩn hoá tên cột về *_member_id.
-- tasks.assignee_id là cột chết (đã bị thay bởi assignee_member_id từ
-- trước, không còn service nào ghi vào nó) — xoá luôn, không rename.
ALTER TABLE operating.tasks DROP COLUMN IF EXISTS assignee_id;
ALTER TABLE strategy.initiatives RENAME COLUMN owner_id TO owner_member_id;
ALTER TABLE strategy.okr_objectives RENAME COLUMN owner_id TO owner_member_id;
ALTER TABLE strategy.projects RENAME COLUMN owner_id TO owner_member_id;
ALTER TABLE strategy.experiments RENAME COLUMN owner_workforce_member_id TO owner_member_id;
ALTER TABLE strategy.decision_records RENAME COLUMN actor_workforce_member_id TO actor_member_id;

