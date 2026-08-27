-- Composite uniqueness (id, workspace_id) trên mọi bảng là target của
-- project link. Bắt buộc phải có để Task 2 tạo composite foreign key
-- (task_id, workspace_id) / (project_id, workspace_id) — Postgres yêu cầu
-- cột được tham chiếu phải có unique constraint khớp đúng.
--
-- PREFLIGHT: chạy services/company/scripts/preflight-workspace-tenancy.sql
-- và xác nhận 0 orphan row TRƯỚC khi áp migration này.

ALTER TABLE strategy.projects
  ADD CONSTRAINT uix_projects_id_workspace UNIQUE (id, workspace_id);

ALTER TABLE strategy.portfolios
  ADD CONSTRAINT uix_portfolios_id_workspace UNIQUE (id, workspace_id);

ALTER TABLE strategy.okr_objectives
  ADD CONSTRAINT uix_okr_objectives_id_workspace UNIQUE (id, workspace_id);

ALTER TABLE operating.tasks
  ADD CONSTRAINT uix_tasks_id_workspace UNIQUE (id, workspace_id);

-- portfolio_projects: chặn liên kết chéo workspace ở tầng DB.
ALTER TABLE strategy.portfolio_projects
  ADD COLUMN IF NOT EXISTS workspace_id BIGINT;

UPDATE strategy.portfolio_projects pp
SET workspace_id = p.workspace_id
FROM strategy.projects p
WHERE p.id = pp.project_id AND pp.workspace_id IS NULL;

ALTER TABLE strategy.portfolio_projects
  ALTER COLUMN workspace_id SET NOT NULL;

ALTER TABLE strategy.portfolio_projects
  ADD CONSTRAINT fk_portfolio_projects_project_ws
  FOREIGN KEY (project_id, workspace_id)
  REFERENCES strategy.projects (id, workspace_id) ON DELETE CASCADE;

ALTER TABLE strategy.portfolio_projects
  ADD CONSTRAINT fk_portfolio_projects_portfolio_ws
  FOREIGN KEY (portfolio_id, workspace_id)
  REFERENCES strategy.portfolios (id, workspace_id) ON DELETE CASCADE;
