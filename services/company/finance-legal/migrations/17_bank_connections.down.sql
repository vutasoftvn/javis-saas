-- services/company/finance-legal/migrations/17_bank_connections.down.sql
DROP INDEX IF EXISTS finance.idx_bank_connections_ws_provider;
DROP TABLE IF EXISTS finance.bank_connections CASCADE;
