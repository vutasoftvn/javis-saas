CREATE SCHEMA IF NOT EXISTS operating;

CREATE TABLE operating.tasks (
  id BIGSERIAL PRIMARY KEY,
  workspace_id BIGINT NOT NULL,
  title TEXT NOT NULL,
  idempotency_key TEXT,
  status TEXT NOT NULL DEFAULT 'todo',
  priority TEXT NOT NULL DEFAULT 'medium',
  planned_start_at TIMESTAMPTZ,
  due_at TIMESTAMPTZ,
  timezone TEXT NOT NULL DEFAULT 'UTC',
  assignee_id BIGINT,
  source TEXT,
  completion_policy TEXT,
  initiative_id BIGINT,
  weekly_commitment_id BIGINT,
  sort_key DOUBLE PRECISION,
  assignee_member_id BIGINT,
  owner_member_id BIGINT,
  execution_mode TEXT,
  function TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  deleted_at TIMESTAMPTZ,
  UNIQUE (workspace_id, idempotency_key)
);

CREATE INDEX idx_tasks_workspace_id ON operating.tasks(workspace_id);
CREATE INDEX idx_tasks_function ON operating.tasks(function);
