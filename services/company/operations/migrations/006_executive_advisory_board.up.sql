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

-- Deliberation Ledger & State Machine

CREATE TABLE IF NOT EXISTS operating.project_executive_deliberations (
  id BIGINT PRIMARY KEY,
  workspace_id BIGINT NOT NULL,
  project_id BIGINT NOT NULL,
  title VARCHAR(255) NOT NULL,
  state VARCHAR(32) NOT NULL DEFAULT 'DRAFT',
  active_frame_version INT NOT NULL DEFAULT 0,
  version INT NOT NULL DEFAULT 1,
  created_by BIGINT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT fk_project_executive_deliberations_proj_ws FOREIGN KEY (project_id, workspace_id)
    REFERENCES strategy.projects(id, workspace_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_project_exec_deliberations_proj
  ON operating.project_executive_deliberations (workspace_id, project_id);

CREATE TABLE IF NOT EXISTS operating.project_executive_deliberation_frames (
  id BIGINT PRIMARY KEY,
  workspace_id BIGINT NOT NULL,
  project_id BIGINT NOT NULL,
  deliberation_id BIGINT NOT NULL REFERENCES operating.project_executive_deliberations(id) ON DELETE CASCADE,
  frame_version INT NOT NULL,
  question TEXT NOT NULL,
  deliberation_type VARCHAR(64) NOT NULL DEFAULT 'STRATEGY',
  deadline TIMESTAMPTZ,
  decision_owner_id BIGINT NOT NULL,
  selected_roles JSONB NOT NULL DEFAULT '[]'::jsonb,
  evidence_sources JSONB NOT NULL DEFAULT '[]'::jsonb,
  critic_required BOOLEAN NOT NULL DEFAULT FALSE,
  redacted_context_ref TEXT,
  framed_by BIGINT NOT NULL,
  framed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT uix_proj_exec_delib_frames_ver UNIQUE (deliberation_id, frame_version)
);

CREATE TABLE IF NOT EXISTS operating.project_executive_deliberation_decisions (
  id BIGINT PRIMARY KEY,
  workspace_id BIGINT NOT NULL,
  project_id BIGINT NOT NULL,
  deliberation_id BIGINT NOT NULL REFERENCES operating.project_executive_deliberations(id) ON DELETE CASCADE,
  decision_type VARCHAR(32) NOT NULL,
  decision_version INT NOT NULL DEFAULT 1,
  actor_id BIGINT NOT NULL,
  notes TEXT,
  modifications JSONB DEFAULT '{}'::jsonb,
  decided_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT uix_proj_exec_delib_decisions_ver UNIQUE (deliberation_id, decision_version)
);

CREATE TABLE IF NOT EXISTS operating.project_executive_deliberation_analyses (
  id BIGINT PRIMARY KEY,
  workspace_id BIGINT NOT NULL,
  project_id BIGINT NOT NULL,
  deliberation_id BIGINT NOT NULL REFERENCES operating.project_executive_deliberations(id) ON DELETE CASCADE,
  frame_version INT NOT NULL,
  role_key VARCHAR(64) NOT NULL,
  run_id TEXT NOT NULL,
  status VARCHAR(32) NOT NULL,
  descriptor JSONB DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT uix_proj_exec_delib_analyses_role UNIQUE (deliberation_id, frame_version, role_key)
);

