-- services/cosa/migrations/26_workspace_agent_policy_and_drop_legacy_companies.up.sql

CREATE TABLE IF NOT EXISTS cosa.workspace_agent_policy (
  id                    BIGINT PRIMARY KEY,
  platform_workspace_id BIGINT NOT NULL REFERENCES cosa.platform_workspaces(id) ON DELETE CASCADE,
  tool_pattern          TEXT NOT NULL,
  decision              TEXT NOT NULL CHECK (decision IN ('ALLOW', 'REQUIRE_APPROVAL', 'DENY')),
  reason                TEXT,
  created_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at            TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_workspace_agent_policy_workspace_id
  ON cosa.workspace_agent_policy(platform_workspace_id);

CREATE UNIQUE INDEX IF NOT EXISTS idx_workspace_agent_policy_workspace_tool
  ON cosa.workspace_agent_policy(platform_workspace_id, tool_pattern);

-- Drop legacy company tables
DROP TABLE IF EXISTS cosa.company_agent_policy CASCADE;
DROP TABLE IF EXISTS cosa.company_entitlements CASCADE;
DROP TABLE IF EXISTS cosa.licenses CASCADE;
DROP TABLE IF EXISTS cosa.company_memberships CASCADE;
DROP TABLE IF EXISTS cosa.companies CASCADE;
