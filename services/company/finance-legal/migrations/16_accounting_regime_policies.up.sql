-- services/company/finance-legal/migrations/16_accounting_regime_policies.up.sql
ALTER TABLE finance.accounting_profiles
  ADD COLUMN IF NOT EXISTS regulation_version_id BIGINT REFERENCES legal.regulation_versions(id) ON DELETE SET NULL,
  ADD COLUMN IF NOT EXISTS applicability_confirmed_at TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS applicability_confirmed_by BIGINT;

CREATE TABLE IF NOT EXISTS finance.accounting_regime_policies (
  id                     BIGINT PRIMARY KEY,
  workspace_id           BIGINT NOT NULL,
  regulation_version_id  BIGINT NOT NULL REFERENCES legal.regulation_versions(id) ON DELETE CASCADE,
  mode                   TEXT NOT NULL,
  effective_from         DATE NOT NULL,
  effective_to           DATE,
  requires_coa           BOOLEAN NOT NULL DEFAULT false,
  requires_double_entry  BOOLEAN NOT NULL DEFAULT false,
  created_at             TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at             TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_accounting_regime_policies_ws_effective
  ON finance.accounting_regime_policies(workspace_id, effective_from);
