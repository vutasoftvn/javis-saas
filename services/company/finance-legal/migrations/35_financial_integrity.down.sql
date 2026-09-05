-- Migration 35 down: Revert financial integrity changes

DROP INDEX IF EXISTS finance.idx_bank_transactions_reconcile_status;
DROP INDEX IF EXISTS finance.idx_accounting_periods_posting_lookup;

ALTER TABLE finance.financial_snapshots
  DROP CONSTRAINT IF EXISTS financial_snapshots_workspace_snapshot_currency_key;

ALTER TABLE finance.financial_snapshots
  ADD CONSTRAINT financial_snapshots_workspace_id_snapshot_date_key
  UNIQUE (workspace_id, snapshot_date);

ALTER TABLE finance.financial_snapshots
  DROP COLUMN IF EXISTS legal_entity_id,
  DROP COLUMN IF EXISTS currency;

ALTER TABLE finance.financial_transactions
  DROP COLUMN IF EXISTS legal_entity_id,
  DROP COLUMN IF EXISTS currency;

ALTER TABLE finance.accounting_periods
  DROP COLUMN IF EXISTS legal_entity_id;
