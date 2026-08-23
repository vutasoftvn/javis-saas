-- services/company/identity/migrations/6_workforce_drop_organizations.up.sql

-- organizations luôn 1:1 với workspace (workspace_id UNIQUE) nên không tạo
-- bounded context mới — chỉ thêm 1 join thừa. workforce_members trỏ thẳng
-- workspace_id.
ALTER TABLE core.workforce_members ADD COLUMN workspace_id BIGINT REFERENCES core.workspaces(id) ON DELETE CASCADE;

UPDATE core.workforce_members wm
SET workspace_id = o.workspace_id
FROM core.organizations o
WHERE wm.organization_id = o.id;

ALTER TABLE core.workforce_members ALTER COLUMN workspace_id SET NOT NULL;
ALTER TABLE core.workforce_members DROP COLUMN organization_id;
DROP TABLE core.organizations;

-- agent_definition_id (BIGINT, không FK) là residue của một workforce-agent
-- row legacy — canonical agent identity giờ là AgentSpec registry của
-- packages/agent_core (id + version dạng text), không phải numeric FK.
ALTER TABLE core.workforce_members RENAME COLUMN agent_definition_id TO agent_spec_id_bigint_deprecated;
ALTER TABLE core.workforce_members ADD COLUMN agent_spec_id TEXT;
ALTER TABLE core.workforce_members ADD COLUMN agent_spec_version TEXT;

UPDATE core.workforce_members
SET agent_spec_id = COALESCE(agent_profile_id, 'unknown-agent-spec'),
    agent_spec_version = '1.0'
WHERE member_type = 'AI_AGENT';

ALTER TABLE core.workforce_members DROP COLUMN agent_spec_id_bigint_deprecated;
ALTER TABLE core.workforce_members DROP COLUMN agent_profile_id;

-- org hierarchy tối thiểu (không tạo workforce.org_units — chưa cần org-chart thật).
ALTER TABLE core.workforce_members ADD COLUMN manager_member_id BIGINT REFERENCES core.workforce_members(id) ON DELETE SET NULL;

-- Chặn hybrid member vô nghĩa ở tầng DB.
ALTER TABLE core.workforce_members ADD CONSTRAINT workforce_members_type_consistency CHECK (
  (member_type = 'HUMAN' AND agent_spec_id IS NULL)
  OR
  (member_type = 'AI_AGENT' AND human_user_id IS NULL)
);
