DROP INDEX IF EXISTS commercial.idx_marketing_experiments_project;
ALTER TABLE commercial.marketing_experiments DROP COLUMN IF EXISTS project_id;

DROP INDEX IF EXISTS commercial.idx_marketing_campaigns_project;
ALTER TABLE commercial.marketing_campaigns DROP COLUMN IF EXISTS project_id;

DROP INDEX IF EXISTS sales.idx_sales_leads_project;
ALTER TABLE sales.sales_leads DROP COLUMN IF EXISTS project_id;

DROP TABLE IF EXISTS sales.contact_projects;
