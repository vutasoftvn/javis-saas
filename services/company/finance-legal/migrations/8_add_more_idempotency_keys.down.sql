-- Rollback 8_add_more_idempotency_keys.up.sql
ALTER TABLE legal.legal_checklist_items DROP CONSTRAINT IF EXISTS legal_checklist_items_workspace_idempotency_key;
ALTER TABLE legal.legal_checklist_items DROP COLUMN IF EXISTS idempotency_key;

ALTER TABLE legal.legal_obligations DROP CONSTRAINT IF EXISTS legal_obligations_workspace_idempotency_key;
ALTER TABLE legal.legal_obligations DROP COLUMN IF EXISTS idempotency_key;

ALTER TABLE finance.accounting_periods DROP CONSTRAINT IF EXISTS accounting_periods_workspace_idempotency_key;
ALTER TABLE finance.accounting_periods DROP COLUMN IF EXISTS idempotency_key;
