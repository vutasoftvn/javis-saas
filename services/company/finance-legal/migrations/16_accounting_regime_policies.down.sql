-- services/company/finance-legal/migrations/16_accounting_regime_policies.down.sql
DROP INDEX IF EXISTS finance.idx_accounting_regime_policies_ws_effective;
DROP TABLE IF EXISTS finance.accounting_regime_policies CASCADE;

ALTER TABLE finance.accounting_profiles
  DROP COLUMN IF EXISTS applicability_confirmed_by,
  DROP COLUMN IF EXISTS applicability_confirmed_at,
  DROP COLUMN IF EXISTS regulation_version_id;
