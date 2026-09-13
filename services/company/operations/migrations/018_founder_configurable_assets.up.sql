-- Migration 018: Founder-Configurable Role, Agent, Skill & Workflow Storage
-- Thêm các bảng quản trị Role, Agent, Deployment, Binding và Audit Events theo Company Business Plane.

CREATE TABLE IF NOT EXISTS operating.workspace_operating_roles (
  id bigint PRIMARY KEY,
  workspace_id bigint NOT NULL,
  role_code text NOT NULL,
  name text NOT NULL,
  description text,
  state text NOT NULL DEFAULT 'ACTIVE',
  created_by bigint NOT NULL,
  version integer NOT NULL DEFAULT 1,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT uix_workspace_operating_roles_ws_code UNIQUE (workspace_id, role_code),
  CONSTRAINT uix_workspace_operating_roles_id_ws UNIQUE (id, workspace_id),
  CONSTRAINT fk_workspace_operating_roles_ws FOREIGN KEY (workspace_id) REFERENCES core.workspaces(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS operating.workspace_agents (
  id bigint PRIMARY KEY,
  workspace_id bigint NOT NULL,
  agent_asset_id text NOT NULL,
  agent_asset_version text NOT NULL,
  agent_definition_hash text NOT NULL,
  workforce_member_id bigint NOT NULL,
  state text NOT NULL DEFAULT 'ACTIVE',
  origin_kind text NOT NULL,
  created_by bigint NOT NULL,
  version integer NOT NULL DEFAULT 1,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT uix_workspace_agents_ws_asset UNIQUE (workspace_id, agent_asset_id),
  CONSTRAINT uix_workspace_agents_id_ws UNIQUE (id, workspace_id),
  CONSTRAINT fk_workspace_agents_ws FOREIGN KEY (workspace_id) REFERENCES core.workspaces(id) ON DELETE CASCADE,
  CONSTRAINT fk_workspace_agents_member FOREIGN KEY (workforce_member_id) REFERENCES core.workforce_members(id) ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS operating.role_agent_bindings (
  id bigint PRIMARY KEY,
  workspace_id bigint NOT NULL,
  role_id bigint NOT NULL,
  workspace_agent_id bigint NOT NULL,
  is_primary boolean NOT NULL DEFAULT false,
  created_by bigint NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT uix_role_agent_bindings_role_agent UNIQUE (workspace_id, role_id, workspace_agent_id),
  CONSTRAINT fk_role_agent_bindings_role FOREIGN KEY (role_id, workspace_id) REFERENCES operating.workspace_operating_roles(id, workspace_id) ON DELETE CASCADE,
  CONSTRAINT fk_role_agent_bindings_agent FOREIGN KEY (workspace_agent_id, workspace_id) REFERENCES operating.workspace_agents(id, workspace_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS operating.project_role_deployments (
  id bigint PRIMARY KEY,
  workspace_id bigint NOT NULL,
  project_id bigint NOT NULL,
  role_id bigint NOT NULL,
  state text NOT NULL DEFAULT 'ACTIVE',
  policy_override jsonb NOT NULL DEFAULT '{}'::jsonb,
  budget_limit jsonb,
  version integer NOT NULL DEFAULT 1,
  created_by bigint NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT uix_project_role_deployments_proj_role UNIQUE (workspace_id, project_id, role_id),
  CONSTRAINT uix_project_role_deployments_id_ws UNIQUE (id, workspace_id),
  CONSTRAINT fk_project_role_deployments_proj FOREIGN KEY (project_id, workspace_id) REFERENCES strategy.projects(id, workspace_id) ON DELETE CASCADE,
  CONSTRAINT fk_project_role_deployments_role FOREIGN KEY (role_id, workspace_id) REFERENCES operating.workspace_operating_roles(id, workspace_id) ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS operating.project_agent_deployments (
  id bigint PRIMARY KEY,
  workspace_id bigint NOT NULL,
  project_id bigint NOT NULL,
  workspace_agent_id bigint NOT NULL,
  project_role_deployment_id bigint,
  state text NOT NULL DEFAULT 'ACTIVE',
  capability_overrides jsonb NOT NULL DEFAULT '[]'::jsonb,
  version integer NOT NULL DEFAULT 1,
  created_by bigint NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT uix_project_agent_deployments_proj_agent UNIQUE (workspace_id, project_id, workspace_agent_id),
  CONSTRAINT uix_project_agent_deployments_id_ws UNIQUE (id, workspace_id),
  CONSTRAINT fk_project_agent_deployments_proj FOREIGN KEY (project_id, workspace_id) REFERENCES strategy.projects(id, workspace_id) ON DELETE CASCADE,
  CONSTRAINT fk_project_agent_deployments_agent FOREIGN KEY (workspace_agent_id, workspace_id) REFERENCES operating.workspace_agents(id, workspace_id) ON DELETE RESTRICT,
  CONSTRAINT fk_project_agent_deployments_role_dep FOREIGN KEY (project_role_deployment_id, workspace_id) REFERENCES operating.project_role_deployments(id, workspace_id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS operating.project_workflow_bindings (
  id bigint PRIMARY KEY,
  workspace_id bigint NOT NULL,
  project_id bigint NOT NULL,
  workflow_asset_id text NOT NULL,
  workflow_asset_version text NOT NULL,
  workflow_definition_hash text NOT NULL,
  state text NOT NULL DEFAULT 'ACTIVE',
  execution_policy jsonb NOT NULL DEFAULT '{}'::jsonb,
  version integer NOT NULL DEFAULT 1,
  created_by bigint NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT uix_project_workflow_bindings_proj_wf UNIQUE (workspace_id, project_id, workflow_asset_id),
  CONSTRAINT fk_project_workflow_bindings_proj FOREIGN KEY (project_id, workspace_id) REFERENCES strategy.projects(id, workspace_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS operating.founder_asset_events (
  id bigint PRIMARY KEY,
  workspace_id bigint NOT NULL,
  project_id bigint,
  actor_id bigint NOT NULL,
  command text NOT NULL,
  target_kind text NOT NULL,
  target_ref jsonb NOT NULL,
  before_hash text,
  after_hash text,
  reason text NOT NULL,
  correlation_id text NOT NULL,
  occurred_at timestamptz NOT NULL DEFAULT now(),
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  CONSTRAINT fk_founder_asset_events_ws FOREIGN KEY (workspace_id) REFERENCES core.workspaces(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_workspace_operating_roles_ws ON operating.workspace_operating_roles(workspace_id);
CREATE INDEX IF NOT EXISTS idx_workspace_agents_ws ON operating.workspace_agents(workspace_id);
CREATE INDEX IF NOT EXISTS idx_project_role_deployments_ws_proj ON operating.project_role_deployments(workspace_id, project_id);
CREATE INDEX IF NOT EXISTS idx_project_agent_deployments_ws_proj ON operating.project_agent_deployments(workspace_id, project_id);
CREATE INDEX IF NOT EXISTS idx_project_workflow_bindings_ws_proj ON operating.project_workflow_bindings(workspace_id, project_id);
CREATE INDEX IF NOT EXISTS idx_founder_asset_events_ws_time ON operating.founder_asset_events(workspace_id, occurred_at DESC);
