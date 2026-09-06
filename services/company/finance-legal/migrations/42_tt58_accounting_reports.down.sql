DROP TABLE IF EXISTS finance.accounting_report_snapshots;
DROP TABLE IF EXISTS finance.accounting_book_entries;
DROP TABLE IF EXISTS finance.accounting_mapping_confirmations;
DROP TABLE IF EXISTS finance.accounting_report_mappings;

DROP INDEX IF EXISTS finance.uix_fiscal_profile_workspace_entity_year;

ALTER TABLE finance.accounting_fiscal_profiles
  ADD CONSTRAINT uix_fiscal_profile_workspace_year UNIQUE (workspace_id, fiscal_year);

ALTER TABLE finance.accounting_fiscal_profiles
  DROP COLUMN IF EXISTS applicability_decision_id,
  DROP COLUMN IF EXISTS mapping_version,
  DROP COLUMN IF EXISTS year_end,
  DROP COLUMN IF EXISTS legal_entity_id;

ALTER TABLE finance.accounting_periods
  DROP COLUMN IF EXISTS version,
  DROP COLUMN IF EXISTS fiscal_profile_id;
