-- BASELINE CANDIDATE (isolated verification only, NOT a production migration path)
-- Domain: services/company -- identity (core schema)
-- Curated subset of REAL migration files, in this order: 1,2,3,6,7,8.
-- SKIPPED: 4_snowflake_ids.up.sql (references core.users/core.workspace_members --
--   names migration 1 never creates; ALSO its snowflake-ID intent (dropping the
--   BIGSERIAL default) is an UNRESOLVED cross-domain disagreement -- see manifest
--   doc drift matrix item #1. NOT silently applied here.)
-- SKIPPED: 5_identity_projection_rework.up.sql (RENAME core.users -> user_projections
--   and core.workspace_members -> workspace_memberships -- migration 1 already
--   creates the tables under the post-rename names, so this file's goal is already
--   met; running it would fail the same way migration 4 does.)
-- Net effect: candidate keeps BIGSERIAL/DEFAULT nextval on identity tables (migration 1's
--   literal declaration), not the app-generated-ID end state migration 4 was written for.

-- source: services/company/identity/migrations/1_create_workspace_user.up.sql
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

-- source: services/company/identity/migrations/2_create_workforce.up.sql
CREATE TABLE IF NOT EXISTS core.organizations (
  id BIGSERIAL PRIMARY KEY,
  workspace_id BIGINT NOT NULL UNIQUE REFERENCES core.workspaces(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  deleted_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS core.workforce_members (
  id BIGSERIAL PRIMARY KEY,
  organization_id BIGINT NOT NULL REFERENCES core.organizations(id) ON DELETE CASCADE,
  member_type TEXT NOT NULL,
  human_user_id BIGINT REFERENCES core.user_projections(id) ON DELETE CASCADE,
  agent_definition_id BIGINT,
  role_title TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'active',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  deleted_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_workforce_members_organization_id ON core.workforce_members(organization_id);
CREATE INDEX IF NOT EXISTS idx_workforce_members_human_user_id ON core.workforce_members(human_user_id);
CREATE INDEX IF NOT EXISTS idx_workforce_members_agent_definition_id ON core.workforce_members(agent_definition_id);

-- source: services/company/identity/migrations/3_add_agent_profile_id.up.sql
ALTER TABLE core.workforce_members ADD COLUMN IF NOT EXISTS agent_profile_id TEXT;

-- source: services/company/identity/migrations/6_workforce_drop_organizations.up.sql
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

-- source: services/company/identity/migrations/7_workforce_full_invariant.up.sql
-- services/company/identity/migrations/7_workforce_full_invariant.up.sql

-- Constraint cũ (migration 6) chỉ chặn field đối nghịch, không bắt buộc field
-- đúng loại phải có mặt — một HUMAN không có human_user_id vẫn pass. Thay
-- bằng constraint đầy đủ 2 chiều theo DB_FINAL_CUTOVER.md §6.3.
ALTER TABLE core.workforce_members DROP CONSTRAINT workforce_members_type_consistency;

ALTER TABLE core.workforce_members ADD CONSTRAINT workforce_members_type_consistency CHECK (
  (member_type = 'HUMAN' AND human_user_id IS NOT NULL AND agent_spec_id IS NULL AND agent_spec_version IS NULL)
  OR
  (member_type = 'AI_AGENT' AND human_user_id IS NULL AND agent_spec_id IS NOT NULL AND agent_spec_version IS NOT NULL)
);

-- source: services/company/identity/migrations/8_workforce_manager_same_workspace.up.sql
-- services/company/identity/migrations/8_workforce_manager_same_workspace.up.sql

-- manager_member_id trước đây chỉ FK tới id toàn cục, không ràng buộc cùng
-- workspace hay chặn self-reference (DB_FINAL_CUTOVER.md §6.4).
ALTER TABLE core.workforce_members ADD CONSTRAINT workforce_members_manager_not_self
  CHECK (manager_member_id IS NULL OR manager_member_id <> id);

-- Composite FK same-workspace: cần unique (id, workspace_id) làm target trước.
ALTER TABLE core.workforce_members ADD CONSTRAINT uq_workforce_members_id_workspace
  UNIQUE (id, workspace_id);

ALTER TABLE core.workforce_members DROP CONSTRAINT workforce_members_manager_member_id_fkey;

ALTER TABLE core.workforce_members ADD CONSTRAINT workforce_members_manager_same_workspace_fkey
  FOREIGN KEY (manager_member_id, workspace_id)
  REFERENCES core.workforce_members(id, workspace_id)
  ON DELETE SET NULL;

