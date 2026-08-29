-- services/company/finance-legal/migrations/21_financial_snapshots_and_txn_provenance.up.sql
ALTER TABLE finance.financial_transactions
  ADD COLUMN IF NOT EXISTS provenance JSONB NOT NULL DEFAULT '{}'::jsonb,
  ADD COLUMN IF NOT EXISTS accounting_document_id BIGINT REFERENCES finance.accounting_documents(id) ON DELETE SET NULL;

CREATE TABLE IF NOT EXISTS finance.financial_snapshots (
  id              BIGINT PRIMARY KEY,
  workspace_id    BIGINT NOT NULL,
  snapshot_date   DATE NOT NULL,
  cash_in         NUMERIC(20, 2) NOT NULL DEFAULT 0,
  cash_out        NUMERIC(20, 2) NOT NULL DEFAULT 0,
  net_burn        NUMERIC(20, 2) NOT NULL DEFAULT 0,
  runway_months   NUMERIC(6, 2),
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (workspace_id, snapshot_date)
);

CREATE INDEX IF NOT EXISTS idx_financial_snapshots_ws_date
  ON finance.financial_snapshots(workspace_id, snapshot_date);
