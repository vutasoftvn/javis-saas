-- Rollback 15_replace_global_project_fks.up.sql
ALTER TABLE strategy.projects
  DROP CONSTRAINT IF EXISTS fk_projects_portfolio_ws;

ALTER TABLE strategy.projects
  ADD CONSTRAINT projects_portfolio_id_fkey
  FOREIGN KEY (portfolio_id)
  REFERENCES strategy.portfolios (id)
  ON DELETE SET NULL;
