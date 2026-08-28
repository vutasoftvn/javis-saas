-- Rollback 13_workspace_composite_uniqueness.up.sql
ALTER TABLE strategy.portfolio_projects DROP CONSTRAINT IF EXISTS fk_portfolio_projects_portfolio_ws;
ALTER TABLE strategy.portfolio_projects DROP CONSTRAINT IF EXISTS fk_portfolio_projects_project_ws;
ALTER TABLE strategy.portfolio_projects DROP COLUMN IF EXISTS workspace_id;

ALTER TABLE operating.tasks DROP CONSTRAINT IF EXISTS uix_tasks_id_workspace;
ALTER TABLE strategy.okr_objectives DROP CONSTRAINT IF EXISTS uix_okr_objectives_id_workspace;
ALTER TABLE strategy.portfolios DROP CONSTRAINT IF EXISTS uix_portfolios_id_workspace;
ALTER TABLE strategy.projects DROP CONSTRAINT IF EXISTS uix_projects_id_workspace;
