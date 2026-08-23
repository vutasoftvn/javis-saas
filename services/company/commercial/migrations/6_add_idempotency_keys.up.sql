-- A retried agent write must not create a duplicate CRM record (blueprint
-- §82). Nullable so existing/plain writes are unaffected; multiple NULLs
-- don't conflict on the unique constraint.
ALTER TABLE sales.accounts ADD COLUMN idempotency_key TEXT;
ALTER TABLE sales.accounts ADD CONSTRAINT accounts_workspace_idempotency_key UNIQUE (workspace_id, idempotency_key);

ALTER TABLE sales.contacts ADD COLUMN idempotency_key TEXT;
ALTER TABLE sales.contacts ADD CONSTRAINT contacts_workspace_idempotency_key UNIQUE (workspace_id, idempotency_key);

ALTER TABLE sales.sales_leads ADD COLUMN idempotency_key TEXT;
ALTER TABLE sales.sales_leads ADD CONSTRAINT sales_leads_workspace_idempotency_key UNIQUE (workspace_id, idempotency_key);

ALTER TABLE sales.sales_opportunities ADD COLUMN idempotency_key TEXT;
ALTER TABLE sales.sales_opportunities ADD CONSTRAINT sales_opportunities_workspace_idempotency_key UNIQUE (workspace_id, idempotency_key);
