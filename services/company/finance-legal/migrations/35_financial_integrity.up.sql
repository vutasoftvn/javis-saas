-- Migration 35: Financial integrity (F07 period lock, F08 concurrent reconciliation claim, F09 currency separation)

ALTER TABLE finance.accounting_periods
  ADD COLUMN IF NOT EXISTS legal_entity_id BIGINT;

ALTER TABLE finance.financial_transactions
  ADD COLUMN IF NOT EXISTS currency TEXT NOT NULL DEFAULT 'VND',
  ADD COLUMN IF NOT EXISTS legal_entity_id BIGINT;

ALTER TABLE finance.financial_snapshots
  ADD COLUMN IF NOT EXISTS currency TEXT NOT NULL DEFAULT 'VND',
  ADD COLUMN IF NOT EXISTS legal_entity_id BIGINT;

-- F09: Cho phép lưu snapshot riêng cho từng loại tiền tệ (VND, USD...) cho cùng một ngày
ALTER TABLE finance.financial_snapshots
  DROP CONSTRAINT IF EXISTS financial_snapshots_workspace_id_snapshot_date_key;

ALTER TABLE finance.financial_snapshots
  ADD CONSTRAINT financial_snapshots_workspace_snapshot_currency_key
  UNIQUE (workspace_id, snapshot_date, currency);

-- Performance and concurrency indexes
CREATE INDEX IF NOT EXISTS idx_accounting_periods_posting_lookup
  ON finance.accounting_periods (workspace_id, status, start_date, end_date);

CREATE INDEX IF NOT EXISTS idx_bank_transactions_reconcile_status
  ON finance.bank_transactions (workspace_id, status);
