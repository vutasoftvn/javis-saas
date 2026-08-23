CREATE SCHEMA IF NOT EXISTS core;

CREATE TABLE IF NOT EXISTS core.workspaces (
  id BIGSERIAL PRIMARY KEY,
  name TEXT NOT NULL,
  company_stage TEXT NOT NULL DEFAULT 'S0_GENESIS',
  platform_company_id TEXT UNIQUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  deleted_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS core.user_projections (
  id BIGSERIAL PRIMARY KEY,
  email TEXT UNIQUE,
  phone TEXT UNIQUE,
  display_name TEXT,
  status TEXT NOT NULL DEFAULT 'active',
  platform_user_id TEXT UNIQUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  deleted_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS core.workspace_memberships (
  id BIGSERIAL PRIMARY KEY,
  workspace_id BIGINT NOT NULL REFERENCES core.workspaces(id) ON DELETE CASCADE,
  user_id BIGINT NOT NULL REFERENCES core.user_projections(id) ON DELETE CASCADE,
  role TEXT NOT NULL DEFAULT 'member',
  platform_membership_id TEXT,
  source_updated_at TIMESTAMPTZ,
  synced_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  deleted_at TIMESTAMPTZ,
  UNIQUE (workspace_id, user_id)
);

CREATE INDEX IF NOT EXISTS idx_workspace_memberships_workspace_id ON core.workspace_memberships(workspace_id);
CREATE INDEX IF NOT EXISTS idx_workspace_memberships_user_id ON core.workspace_memberships(user_id);
