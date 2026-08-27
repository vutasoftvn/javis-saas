-- Replace global project/portfolio foreign key with workspace-scoped composite FK.
-- strategy.projects.portfolio_id currently has a plain FK to strategy.portfolios(id),
-- which allows cross-workspace references. This migration replaces it with a
-- composite FK (portfolio_id, workspace_id) → strategy.portfolios(id, workspace_id),
-- preventing any cross-workspace portfolio references.

ALTER TABLE strategy.projects
  DROP CONSTRAINT projects_portfolio_id_fkey;

ALTER TABLE strategy.projects
  ADD CONSTRAINT fk_projects_portfolio_ws
  FOREIGN KEY (portfolio_id, workspace_id)
  REFERENCES strategy.portfolios (id, workspace_id)
  ON DELETE SET NULL (portfolio_id);
