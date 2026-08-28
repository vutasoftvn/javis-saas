-- Rollback 8_actor_naming_standardization.up.sql
ALTER TABLE sales.customers RENAME COLUMN owner_member_id TO owner_id;
ALTER TABLE sales.sales_opportunities RENAME COLUMN owner_member_id TO owner_id;
ALTER TABLE sales.sales_leads RENAME COLUMN owner_member_id TO owner_id;
ALTER TABLE sales.contacts RENAME COLUMN owner_member_id TO owner_id;
ALTER TABLE sales.accounts RENAME COLUMN owner_member_id TO owner_id;
