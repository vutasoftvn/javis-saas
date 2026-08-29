-- services/company/finance-legal/migrations/19_bank_transactions.down.sql
DROP INDEX IF EXISTS finance.idx_bank_transactions_ws_posted;
DROP INDEX IF EXISTS finance.idx_bank_transactions_ws_status;
DROP TABLE IF EXISTS finance.bank_transactions CASCADE;
