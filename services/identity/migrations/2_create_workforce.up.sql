CREATE TABLE core.organizations (
  id BIGSERIAL PRIMARY KEY,
  workspace_id BIGINT NOT NULL UNIQUE REFERENCES core.workspaces(id),
  name TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE core.workforce_members (
  id BIGSERIAL PRIMARY KEY,
  organization_id BIGINT NOT NULL REFERENCES core.organizations(id),
  member_type TEXT NOT NULL,
  human_user_id BIGINT REFERENCES core.users(id),
  agent_definition_id BIGINT,
  role_title TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'active',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_workforce_members_organization_id ON core.workforce_members(organization_id);
CREATE INDEX idx_workforce_members_human_user_id ON core.workforce_members(human_user_id);
CREATE INDEX idx_workforce_members_agent_definition_id ON core.workforce_members(agent_definition_id);
