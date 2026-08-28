-- Rollback 7_add_transaction_idempotency_key.up.sql
ALTER TABLE finance.financial_transactions DROP CONSTRAINT IF EXISTS financial_transactions_workspace_idempotency_key;
ALTER TABLE finance.financial_transactions DROP COLUMN IF EXISTS idempotency_key;
