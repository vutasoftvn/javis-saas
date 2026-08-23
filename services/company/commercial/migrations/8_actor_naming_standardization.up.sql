-- services/company/commercial/migrations/8_actor_naming_standardization.up.sql

-- Đồng bộ với operations/migrations/12: canonical actor field name là
-- *_member_id trên toàn bộ business schema.
ALTER TABLE sales.accounts RENAME COLUMN owner_id TO owner_member_id;
ALTER TABLE sales.contacts RENAME COLUMN owner_id TO owner_member_id;
ALTER TABLE sales.sales_leads RENAME COLUMN owner_id TO owner_member_id;
ALTER TABLE sales.sales_opportunities RENAME COLUMN owner_id TO owner_member_id;
ALTER TABLE sales.customers RENAME COLUMN owner_id TO owner_member_id;
