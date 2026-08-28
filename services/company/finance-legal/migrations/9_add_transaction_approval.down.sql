-- Rollback 9_add_transaction_approval.up.sql
ALTER TABLE finance.financial_transactions
  DROP COLUMN IF EXISTS approved_at,
  DROP COLUMN IF EXISTS approved_by_user_id,
  DROP COLUMN IF EXISTS approval_status;
