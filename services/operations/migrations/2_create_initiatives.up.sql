CREATE SCHEMA IF NOT EXISTS strategy;

CREATE TABLE strategy.initiatives (
  id BIGSERIAL PRIMARY KEY,
  workspace_id BIGINT NOT NULL,
  brain_id BIGINT,
  project_id BIGINT,
  offering_id BIGINT,
  title TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'active',
  owner_id BIGINT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_initiatives_workspace_id ON strategy.initiatives(workspace_id);

ALTER TABLE operating.tasks
  ADD CONSTRAINT fk_tasks_initiative_id FOREIGN KEY (initiative_id) REFERENCES strategy.initiatives(id);
