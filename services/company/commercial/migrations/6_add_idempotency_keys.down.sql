-- Rollback 6_add_idempotency_keys.up.sql
ALTER TABLE sales.sales_opportunities DROP CONSTRAINT IF EXISTS sales_opportunities_workspace_idempotency_key;
ALTER TABLE sales.sales_opportunities DROP COLUMN IF EXISTS idempotency_key;

ALTER TABLE sales.sales_leads DROP CONSTRAINT IF EXISTS sales_leads_workspace_idempotency_key;
ALTER TABLE sales.sales_leads DROP COLUMN IF EXISTS idempotency_key;

ALTER TABLE sales.contacts DROP CONSTRAINT IF EXISTS contacts_workspace_idempotency_key;
ALTER TABLE sales.contacts DROP COLUMN IF EXISTS idempotency_key;

ALTER TABLE sales.accounts DROP CONSTRAINT IF EXISTS accounts_workspace_idempotency_key;
ALTER TABLE sales.accounts DROP COLUMN IF EXISTS idempotency_key;
