-- Migration 37 down

DROP INDEX IF EXISTS finance.idx_ingestion_dlq_conn;
DROP TABLE IF EXISTS finance.ingestion_dlq CASCADE;

DROP INDEX IF EXISTS finance.idx_cas_normalizer_log_conn;
DROP INDEX IF EXISTS finance.idx_cas_normalizer_log_dedup;
DROP TABLE IF EXISTS finance.cas_normalizer_log CASCADE;

DROP INDEX IF EXISTS finance.idx_cas_sync_inbox_conn;
DROP INDEX IF EXISTS finance.idx_cas_sync_inbox_due;
DROP INDEX IF EXISTS finance.idx_cas_sync_inbox_dedup;
DROP TABLE IF EXISTS finance.cas_sync_inbox CASCADE;

DROP INDEX IF EXISTS finance.idx_bank_transactions_conn_ext_unique;

ALTER TABLE finance.bank_connections
  DROP COLUMN IF EXISTS sync_coverage_start,
  DROP COLUMN IF EXISTS sync_locked_until,
  DROP COLUMN IF EXISTS sync_error_count,
  DROP COLUMN IF EXISTS sync_error,
  DROP COLUMN IF EXISTS sync_cursor;
