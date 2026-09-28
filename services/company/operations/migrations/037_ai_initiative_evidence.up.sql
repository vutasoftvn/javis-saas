-- Migration 037: AI Initiative Evidence and Audit Contracts

-- 1. Value Contracts
CREATE TABLE IF NOT EXISTS strategy.ai_initiative_value_contracts (
  id BIGINT PRIMARY KEY,
  workspace_id BIGINT NOT NULL,
  project_id BIGINT NOT NULL,
  initiative_id BIGINT NOT NULL REFERENCES strategy.initiatives(id) ON DELETE CASCADE,
  revision INTEGER NOT NULL DEFAULT 1,
  metric_contract_id TEXT NOT NULL,
  baseline_value NUMERIC(18, 4) NOT NULL,
  baseline_observed_at TIMESTAMPTZ NOT NULL,
  baseline_source_ref TEXT NOT NULL,
  target_value NUMERIC(18, 4) NOT NULL,
  target_by TIMESTAMPTZ NOT NULL,
  measurement_window TEXT NOT NULL,
  unit TEXT NOT NULL,
  scoring_direction TEXT NOT NULL DEFAULT 'ASC',
  expected_value_method TEXT NOT NULL,
  expected_value_amount NUMERIC(18, 4),
  currency TEXT NOT NULL DEFAULT 'VND',
  adoption_target NUMERIC(18, 4),
  adoption_window TEXT,
  measurement_owner_member_id BIGINT NOT NULL REFERENCES core.workforce_members(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT uix_ai_val_contract_init_rev UNIQUE (initiative_id, revision)
);

CREATE INDEX IF NOT EXISTS idx_ai_val_contract_lookup
  ON strategy.ai_initiative_value_contracts(workspace_id, project_id, initiative_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_ai_val_contract_owner
  ON strategy.ai_initiative_value_contracts(measurement_owner_member_id);

-- 2. Data Readiness Assessments
CREATE TABLE IF NOT EXISTS strategy.ai_initiative_data_readiness_assessments (
  id BIGINT PRIMARY KEY,
  workspace_id BIGINT NOT NULL,
  project_id BIGINT NOT NULL,
  initiative_id BIGINT NOT NULL REFERENCES strategy.initiatives(id) ON DELETE CASCADE,
  revision INTEGER NOT NULL DEFAULT 1,
  source_refs JSONB NOT NULL DEFAULT '[]',
  classification TEXT NOT NULL,
  access_authority_ref TEXT NOT NULL,
  freshness_slo TEXT NOT NULL,
  quality_dimensions JSONB NOT NULL DEFAULT '{}',
  metadata_owner_member_id BIGINT NOT NULL REFERENCES core.workforce_members(id),
  retrieval_mode TEXT NOT NULL DEFAULT 'none',
  knowledge_snapshot_ref TEXT,
  assessment_status TEXT NOT NULL,
  evidence_refs JSONB NOT NULL DEFAULT '[]',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT uix_ai_dra_init_rev UNIQUE (initiative_id, revision),
  CONSTRAINT chk_ai_dra_status CHECK (assessment_status IN ('NOT_READY', 'CONDITIONAL', 'READY')),
  CONSTRAINT chk_ai_dra_retrieval_mode CHECK (retrieval_mode IN ('none', 'lexical', 'semantic'))
);

CREATE INDEX IF NOT EXISTS idx_ai_dra_lookup
  ON strategy.ai_initiative_data_readiness_assessments(workspace_id, project_id, initiative_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_ai_dra_owner
  ON strategy.ai_initiative_data_readiness_assessments(metadata_owner_member_id);

-- 3. Budget Policies
CREATE TABLE IF NOT EXISTS strategy.ai_initiative_budget_policies (
  id BIGINT PRIMARY KEY,
  workspace_id BIGINT NOT NULL,
  project_id BIGINT NOT NULL,
  initiative_id BIGINT NOT NULL REFERENCES strategy.initiatives(id) ON DELETE CASCADE,
  revision INTEGER NOT NULL DEFAULT 1,
  period TEXT NOT NULL DEFAULT 'MONTHLY',
  currency TEXT NOT NULL DEFAULT 'USD',
  soft_cost_threshold NUMERIC(18, 4) NOT NULL,
  hard_cost_threshold NUMERIC(18, 4) NOT NULL,
  action_on_breach TEXT NOT NULL DEFAULT 'WARN',
  allowed_models JSONB NOT NULL DEFAULT '[]',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT uix_ai_budget_init_rev UNIQUE (initiative_id, revision),
  CONSTRAINT chk_ai_budget_action CHECK (action_on_breach IN ('WARN', 'REQUIRE_APPROVAL', 'PAUSE_INITIATIVE'))
);

CREATE INDEX IF NOT EXISTS idx_ai_budget_lookup
  ON strategy.ai_initiative_budget_policies(workspace_id, project_id, initiative_id, created_at DESC);

-- 4. Decisions
CREATE TABLE IF NOT EXISTS strategy.ai_initiative_decisions (
  id BIGINT PRIMARY KEY,
  workspace_id BIGINT NOT NULL,
  project_id BIGINT NOT NULL,
  initiative_id BIGINT NOT NULL REFERENCES strategy.initiatives(id) ON DELETE CASCADE,
  revision INTEGER NOT NULL,
  decision TEXT NOT NULL,
  from_state TEXT NOT NULL,
  to_state TEXT NOT NULL,
  actor_member_id BIGINT REFERENCES core.workforce_members(id),
  reason_code TEXT NOT NULL,
  reason TEXT,
  gate_snapshot JSONB NOT NULL DEFAULT '{}',
  idempotency_key TEXT,
  decided_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_ai_decisions_lookup
  ON strategy.ai_initiative_decisions(workspace_id, project_id, initiative_id, decided_at DESC);

CREATE INDEX IF NOT EXISTS idx_ai_decisions_actor
  ON strategy.ai_initiative_decisions(actor_member_id);

CREATE UNIQUE INDEX IF NOT EXISTS uix_ai_decisions_init_idem
  ON strategy.ai_initiative_decisions(initiative_id, idempotency_key)
  WHERE idempotency_key IS NOT NULL;

-- 5. Value Measurements
CREATE TABLE IF NOT EXISTS strategy.ai_initiative_value_measurements (
  id BIGINT PRIMARY KEY,
  workspace_id BIGINT NOT NULL,
  project_id BIGINT NOT NULL,
  initiative_id BIGINT NOT NULL REFERENCES strategy.initiatives(id) ON DELETE CASCADE,
  metric_contract_id TEXT NOT NULL,
  observed_value NUMERIC(18, 4),
  state TEXT NOT NULL DEFAULT 'PRESENT',
  observed_at TIMESTAMPTZ NOT NULL,
  window_start TIMESTAMPTZ NOT NULL,
  window_end TIMESTAMPTZ NOT NULL,
  quality_state TEXT NOT NULL DEFAULT 'GOOD',
  missing_data_state TEXT,
  measurement_owner_member_id BIGINT REFERENCES core.workforce_members(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT chk_ai_measurement_state CHECK (state IN ('PRESENT', 'UNAVAILABLE', 'INVALID'))
);

CREATE INDEX IF NOT EXISTS idx_ai_measurements_lookup
  ON strategy.ai_initiative_value_measurements(workspace_id, project_id, initiative_id, observed_at DESC);

CREATE INDEX IF NOT EXISTS idx_ai_measurements_owner
  ON strategy.ai_initiative_value_measurements(measurement_owner_member_id);
