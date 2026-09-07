-- Migration 33: Workspace and user module visibility preferences

CREATE TABLE IF NOT EXISTS cosa.workspace_module_configs (
  workspace_id  BIGINT NOT NULL REFERENCES cosa.workspaces(id) ON DELETE CASCADE,
  module_key    TEXT NOT NULL CHECK (module_key IN ('finance', 'legal', 'crm')),
  enabled       BOOLEAN NOT NULL DEFAULT true,
  updated_by    TEXT NOT NULL,
  updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  PRIMARY KEY (workspace_id, module_key)
);

CREATE TABLE IF NOT EXISTS cosa.user_workspace_module_preferences (
  workspace_id  BIGINT NOT NULL REFERENCES cosa.workspaces(id) ON DELETE CASCADE,
  user_id       BIGINT NOT NULL REFERENCES cosa.users(id) ON DELETE CASCADE,
  module_key    TEXT NOT NULL CHECK (module_key IN ('finance', 'legal', 'crm')),
  visible       BOOLEAN NOT NULL DEFAULT true,
  updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  PRIMARY KEY (workspace_id, user_id, module_key)
);
