-- A retried financial-transaction write must not create a duplicate charge
-- (blueprint §82 — business writes need an idempotency key). Nullable so
-- existing/plain writes are unaffected; multiple NULLs don't conflict.
ALTER TABLE finance.financial_transactions ADD COLUMN idempotency_key TEXT;
ALTER TABLE finance.financial_transactions ADD CONSTRAINT financial_transactions_workspace_idempotency_key
  UNIQUE (workspace_id, idempotency_key);
