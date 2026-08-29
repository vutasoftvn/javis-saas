-- services/company/finance-legal/migrations/21_financial_snapshots_and_txn_provenance.down.sql
DROP INDEX IF EXISTS finance.idx_financial_snapshots_ws_date;
DROP TABLE IF EXISTS finance.financial_snapshots CASCADE;

ALTER TABLE finance.financial_transactions
  DROP COLUMN IF EXISTS accounting_document_id,
  DROP COLUMN IF EXISTS provenance;
