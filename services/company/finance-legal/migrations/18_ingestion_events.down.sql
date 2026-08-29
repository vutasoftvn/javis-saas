-- services/company/finance-legal/migrations/18_ingestion_events.down.sql
DROP INDEX IF EXISTS finance.idx_ingestion_events_status_received;
DROP TABLE IF EXISTS finance.ingestion_events CASCADE;
