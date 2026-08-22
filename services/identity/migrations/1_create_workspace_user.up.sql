CREATE SCHEMA IF NOT EXISTS core;

CREATE TABLE core.workspaces (
  id BIGSERIAL PRIMARY KEY,
  name TEXT NOT NULL,
  company_stage TEXT NOT NULL DEFAULT 'S0_GENESIS',
  platform_company_id TEXT UNIQUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE core.users (
  id BIGSERIAL PRIMARY KEY,
  email TEXT UNIQUE,
  phone TEXT UNIQUE,
  password_hash TEXT,
  display_name TEXT,
  status TEXT NOT NULL DEFAULT 'active',
  platform_user_id TEXT UNIQUE,
  role TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE core.workspace_members (
  id BIGSERIAL PRIMARY KEY,
  workspace_id BIGINT NOT NULL REFERENCES core.workspaces(id),
  user_id BIGINT NOT NULL REFERENCES core.users(id),
  role TEXT NOT NULL DEFAULT 'member',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_workspace_members_workspace_id ON core.workspace_members(workspace_id);
CREATE INDEX idx_workspace_members_user_id ON core.workspace_members(user_id);
