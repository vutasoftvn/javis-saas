CREATE SCHEMA IF NOT EXISTS commercial;

CREATE TABLE commercial.invoices (
    id BIGSERIAL PRIMARY KEY,
    workspace_id BIGINT NOT NULL,
    customer_id BIGINT REFERENCES sales.customers(id) ON DELETE SET NULL,
    invoice_number VARCHAR(100) NOT NULL,
    amount DOUBLE PRECISION NOT NULL,
    currency VARCHAR(10) NOT NULL DEFAULT 'VND',
    status VARCHAR(50) NOT NULL DEFAULT 'draft',
    due_date TIMESTAMPTZ,
    paid_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uix_invoices_workspace_number UNIQUE (workspace_id, invoice_number)
);

CREATE INDEX idx_invoices_workspace ON commercial.invoices(workspace_id);

CREATE TABLE commercial.subscriptions (
    id BIGSERIAL PRIMARY KEY,
    workspace_id BIGINT NOT NULL,
    customer_id BIGINT REFERENCES sales.customers(id) ON DELETE SET NULL,
    plan_name VARCHAR(100) NOT NULL,
    billing_cycle VARCHAR(50) NOT NULL DEFAULT 'monthly',
    price DOUBLE PRECISION NOT NULL,
    currency VARCHAR(10) NOT NULL DEFAULT 'VND',
    status VARCHAR(50) NOT NULL DEFAULT 'active',
    current_period_start TIMESTAMPTZ,
    current_period_end TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_subscriptions_workspace ON commercial.subscriptions(workspace_id);
