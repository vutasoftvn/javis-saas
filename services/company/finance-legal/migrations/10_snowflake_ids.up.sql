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
