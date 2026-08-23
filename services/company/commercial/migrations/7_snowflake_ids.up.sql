-- Migrate commercial and sales tables to Snowflake IDs
-- Truncate all data and drop auto-increment defaults
TRUNCATE TABLE commercial.campaign_assets, commercial.invoices, commercial.marketing_campaigns, commercial.marketing_contexts, commercial.marketing_forms, commercial.marketing_lead_intakes, commercial.subscriptions, sales.accounts, sales.contacts, sales.customers, sales.sales_leads, sales.sales_opportunities CASCADE;

ALTER TABLE commercial.campaign_assets ALTER COLUMN id DROP DEFAULT;
ALTER TABLE commercial.invoices ALTER COLUMN id DROP DEFAULT;
ALTER TABLE commercial.marketing_campaigns ALTER COLUMN id DROP DEFAULT;
ALTER TABLE commercial.marketing_contexts ALTER COLUMN id DROP DEFAULT;
ALTER TABLE commercial.marketing_forms ALTER COLUMN id DROP DEFAULT;
ALTER TABLE commercial.marketing_lead_intakes ALTER COLUMN id DROP DEFAULT;
ALTER TABLE commercial.subscriptions ALTER COLUMN id DROP DEFAULT;
ALTER TABLE sales.accounts ALTER COLUMN id DROP DEFAULT;
ALTER TABLE sales.contacts ALTER COLUMN id DROP DEFAULT;
ALTER TABLE sales.customers ALTER COLUMN id DROP DEFAULT;
ALTER TABLE sales.sales_leads ALTER COLUMN id DROP DEFAULT;
ALTER TABLE sales.sales_opportunities ALTER COLUMN id DROP DEFAULT;
