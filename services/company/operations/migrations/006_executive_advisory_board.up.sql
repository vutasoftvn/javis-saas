-- 006_executive_advisory_board.up.sql
-- Executive Advisory Board settings, role activations, and activation audit events.

CREATE TABLE IF NOT EXISTS operating.project_executive_board_settings (
  workspace_id BIGINT NOT NULL,
  project_id BIGINT NOT NULL,
  preset_key VARCHAR(64) NOT NULL,
  version INT NOT NULL DEFAULT 1,
  selected_by BIGINT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT pk_project_executive_board_settings PRIMARY KEY (workspace_id, project_id),
  CONSTRAINT fk_project_executive_board_settings_proj_ws FOREIGN KEY (project_id, workspace_id)
    REFERENCES strategy.projects(id, workspace_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS operating.project_executive_role_activations (
  id BIGINT PRIMARY KEY,
  workspace_id BIGINT NOT NULL,
  project_id BIGINT NOT NULL,
  role_key VARCHAR(64) NOT NULL,
  state VARCHAR(32) NOT NULL,
  activation_source VARCHAR(64) NOT NULL,
  version INT NOT NULL DEFAULT 1,
  actor_id BIGINT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT uix_project_executive_role_activations_ws_proj_role UNIQUE (workspace_id, project_id, role_key),
  CONSTRAINT fk_project_executive_role_activations_proj_ws FOREIGN KEY (project_id, workspace_id)
    REFERENCES strategy.projects(id, workspace_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_project_executive_role_activations_proj
  ON operating.project_executive_role_activations (workspace_id, project_id);

CREATE TABLE IF NOT EXISTS operating.project_executive_role_activation_events (
  id BIGINT PRIMARY KEY,
  workspace_id BIGINT NOT NULL,
  project_id BIGINT NOT NULL,
  role_key VARCHAR(64) NOT NULL,
  activation_id BIGINT NOT NULL REFERENCES operating.project_executive_role_activations(id) ON DELETE CASCADE,
  from_state VARCHAR(32),
  to_state VARCHAR(32) NOT NULL,
  actor_id BIGINT NOT NULL,
  version INT NOT NULL,
  payload JSONB NOT NULL DEFAULT '{}'::jsonb,
  occurred_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_project_exec_role_act_events_act
  ON operating.project_executive_role_activation_events (activation_id, occurred_at);
