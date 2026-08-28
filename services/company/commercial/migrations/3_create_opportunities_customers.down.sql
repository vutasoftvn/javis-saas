-- Rollback 3_create_opportunities_customers.up.sql
DROP TABLE IF EXISTS sales.customers CASCADE;
DROP TABLE IF EXISTS sales.sales_opportunities CASCADE;
