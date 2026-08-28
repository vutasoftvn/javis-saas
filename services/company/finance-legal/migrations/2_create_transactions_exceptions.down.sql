-- Rollback 2_create_transactions_exceptions.up.sql
DROP TABLE IF EXISTS finance.transaction_exceptions CASCADE;
DROP TABLE IF EXISTS finance.financial_transactions CASCADE;
