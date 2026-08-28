-- Rollback 5_create_billing_domain.up.sql
DROP TABLE IF EXISTS commercial.invoices CASCADE;
DROP TABLE IF EXISTS commercial.subscriptions CASCADE;
