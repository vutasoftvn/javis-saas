-- baseline_v1 — thay thế retired_pre_baseline_v1/{1,2,3,4,5,6,7,8} (4 và 5
-- gãy fresh bootstrap, xem retired_pre_baseline_v1/README.md). Nội dung dựa
-- trực tiếp trên
-- docs/architecture/generated/baseline_candidate/company_identity_baseline_v1.sql
-- (đã fresh-Postgres verify PASS — xem docs/architecture/DB_BASELINE_PREPARATION.md
-- mục 6) — giữ nguyên chuỗi ALTER/constraint đã proven cho workforce_members
-- (không viết lại từ đầu), chỉ sửa theo quyết định đã chốt tại
-- COSA_FINAL_INTEGRATION_AND_LEGACY_EXIT_PLAN_2026-08-25.md §29.4:
--   1. id BIGSERIAL -> id BIGINT (không DEFAULT) cho workspaces/
--      user_projections/workspace_memberships/workforce_members —
--      Snowflake ID sinh ở tầng app qua
--      services/company/shared/services/snowflake.service.ts::generateSnowflake().
--      Khớp đúng services/company/shared/db/schema/identity.ts (đã khai báo
--      bigint({mode:"bigint"}).primaryKey() không default từ trước) và app
--      đã gọi generateSnowflake() thật ở identity/services/{workspace,
--      workforce,sync}.service.ts — DEFAULT BIGSERIAL cũ chưa từng thực sự
--      được dùng, xoá nó không đổi hành vi runtime hiện có.
--      core.organizations (tạo rồi DROP ngay trong file này) giữ BIGSERIAL —
--      không tồn tại ở schema đích nên không cần đổi ID strategy.
--   2. Thêm CHECK (email IS NOT NULL OR phone IS NOT NULL) trên
--      core.user_projections.

CREATE SCHEMA IF NOT EXISTS core;

CREATE TABLE IF NOT EXISTS core.workspaces (
  id BIGINT PRIMARY KEY,
  name TEXT NOT NULL,
  company_stage TEXT NOT NULL DEFAULT 'S0_GENESIS',
  platform_company_id TEXT UNIQUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  deleted_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS core.user_projections (
  id BIGINT PRIMARY KEY,
  email TEXT UNIQUE,
  phone TEXT UNIQUE,
  display_name TEXT,
  status TEXT NOT NULL DEFAULT 'active',
  platform_user_id TEXT UNIQUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  deleted_at TIMESTAMPTZ,
  CONSTRAINT user_projections_email_or_phone_required CHECK (email IS NOT NULL OR phone IS NOT NULL)
);

CREATE TABLE IF NOT EXISTS core.workspace_memberships (
  id BIGINT PRIMARY KEY,
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

-- core.organizations: bảng tạm thời (tạo rồi DROP ngay dưới) để giữ đúng
-- chuỗi thao tác đã proven fresh-Postgres cho workforce_members — không
-- tồn tại ở schema đích nên KHÔNG đổi ID strategy (BIGSERIAL ở đây vô hại,
-- vì bảng bị xoá trước khi baseline này chạy xong).
CREATE TABLE IF NOT EXISTS core.organizations (
  id BIGSERIAL PRIMARY KEY,
  workspace_id BIGINT NOT NULL UNIQUE REFERENCES core.workspaces(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  deleted_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS core.workforce_members (
  id BIGINT PRIMARY KEY,
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

ALTER TABLE core.workforce_members ADD COLUMN IF NOT EXISTS agent_profile_id TEXT;

-- organizations luôn 1:1 với workspace (workspace_id UNIQUE) nên không giữ
-- làm bounded context riêng — chỉ thêm 1 join thừa. workforce_members trỏ
-- thẳng workspace_id (đúng schema đích, xem
-- services/company/shared/db/schema/identity.ts).
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
-- packages/agent (id + version dạng text), không phải numeric FK.
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

-- Constraint đầy đủ 2 chiều (không chỉ chặn field đối nghịch, còn bắt buộc
-- field đúng loại phải có mặt) theo DB_FINAL_CUTOVER.md §6.3 — viết thẳng
-- bản cuối, không qua bản trung gian "chỉ chặn field đối nghịch" của
-- migration 6 cũ nữa.
ALTER TABLE core.workforce_members ADD CONSTRAINT workforce_members_type_consistency CHECK (
  (member_type = 'HUMAN' AND human_user_id IS NOT NULL AND agent_spec_id IS NULL AND agent_spec_version IS NULL)
  OR
  (member_type = 'AI_AGENT' AND human_user_id IS NULL AND agent_spec_id IS NOT NULL AND agent_spec_version IS NOT NULL)
);

-- manager_member_id: chặn self-reference + bắt buộc cùng workspace
-- (DB_FINAL_CUTOVER.md §6.4).
ALTER TABLE core.workforce_members ADD CONSTRAINT workforce_members_manager_not_self
  CHECK (manager_member_id IS NULL OR manager_member_id <> id);

ALTER TABLE core.workforce_members ADD CONSTRAINT uq_workforce_members_id_workspace
  UNIQUE (id, workspace_id);

ALTER TABLE core.workforce_members DROP CONSTRAINT workforce_members_manager_member_id_fkey;

ALTER TABLE core.workforce_members ADD CONSTRAINT workforce_members_manager_same_workspace_fkey
  FOREIGN KEY (manager_member_id, workspace_id)
  REFERENCES core.workforce_members(id, workspace_id)
  ON DELETE SET NULL;
