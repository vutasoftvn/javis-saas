-- Same reasoning as 7_add_transaction_idempotency_key.up.sql, extended to
-- the other agent-writable finance/legal tables (blueprint §82).
ALTER TABLE finance.accounting_periods ADD COLUMN idempotency_key TEXT;
ALTER TABLE finance.accounting_periods ADD CONSTRAINT accounting_periods_workspace_idempotency_key UNIQUE (workspace_id, idempotency_key);

ALTER TABLE legal.legal_obligations ADD COLUMN idempotency_key TEXT;
ALTER TABLE legal.legal_obligations ADD CONSTRAINT legal_obligations_workspace_idempotency_key UNIQUE (workspace_id, idempotency_key);

ALTER TABLE legal.legal_checklist_items ADD COLUMN idempotency_key TEXT;
ALTER TABLE legal.legal_checklist_items ADD CONSTRAINT legal_checklist_items_workspace_idempotency_key UNIQUE (workspace_id, idempotency_key);
