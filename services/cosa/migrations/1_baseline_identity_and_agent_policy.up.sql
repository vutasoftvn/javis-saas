-- baseline_v1 — thay thế retired_pre_baseline_v1/{1,2,3,4,5} (5 gãy fresh
-- bootstrap, xem retired_pre_baseline_v1/README.md). Nội dung dựa trực tiếp
-- trên docs/architecture/generated/baseline_candidate/cosa_identity_baseline_v1.sql
-- (đã fresh-Postgres verify PASS — xem docs/architecture/DB_BASELINE_PREPARATION.md
-- mục 6), chỉ sửa 3 điểm theo quyết định đã chốt tại
-- COSA_FINAL_INTEGRATION_AND_LEGACY_EXIT_PLAN_2026-08-25.md §29.4:
--   1. id BIGSERIAL -> id BIGINT (không DEFAULT) cho users/companies/
--      company_memberships/licenses — Snowflake ID sinh ở tầng app qua
--      services/cosa/services/snowflake.service.ts::generateSnowflakeStr().
--      App đã gọi hàm này và truyền id tường minh ở auth.service.ts/
--      company.service.ts từ trước — DEFAULT BIGSERIAL cũ chưa từng thực sự
--      được dùng, xoá nó không đổi hành vi runtime hiện có.
--   2. Thêm CHECK (email IS NOT NULL OR phone IS NOT NULL) trên cosa.users.
--   3. Seed cosa.plans đủ 4 tier free/starter/pro/enterprise (thay vì chỉ
--      starter) — limits/features per-tier cụ thể là quyết định sản phẩm
--      chưa chốt, tạm dùng chung 1 bộ default cho cả 4 tier.

CREATE SCHEMA IF NOT EXISTS cosa;

CREATE TABLE IF NOT EXISTS cosa.roles (
  id TEXT PRIMARY KEY,
  scope TEXT NOT NULL,
  level INTEGER NOT NULL,
  description TEXT
);

INSERT INTO cosa.roles (id, scope, level, description) VALUES
  ('superadmin', 'platform', 100, 'Super Administrator'),
  ('admin', 'platform', 80, 'Platform Administrator'),
  ('support', 'platform', 50, 'Support Specialist'),
  ('founder', 'company', 90, 'Company Founder / Owner'),
  ('co-founder', 'company', 80, 'Company Co-founder'),
  ('user', 'company', 10, 'Regular Member'),
  ('auditor', 'company', 20, 'Read-only company auditor')
ON CONFLICT (id) DO NOTHING;

CREATE TABLE IF NOT EXISTS cosa.users (
  id BIGINT PRIMARY KEY,
  email TEXT UNIQUE,
  phone TEXT UNIQUE,
  hashed_password TEXT NOT NULL,
  is_platform_admin BOOLEAN NOT NULL DEFAULT FALSE,
  platform_role_id TEXT REFERENCES cosa.roles(id),
  status TEXT NOT NULL DEFAULT 'active',
  last_login_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  deleted_at TIMESTAMPTZ,
  CONSTRAINT users_email_or_phone_required CHECK (email IS NOT NULL OR phone IS NOT NULL)
);

CREATE INDEX IF NOT EXISTS idx_cp_users_email ON cosa.users(email);
CREATE INDEX IF NOT EXISTS idx_cp_users_phone ON cosa.users(phone);

CREATE TABLE IF NOT EXISTS cosa.profiles (
  user_id BIGINT PRIMARY KEY REFERENCES cosa.users(id) ON DELETE CASCADE,
  full_name TEXT,
  avatar_url TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS cosa.companies (
  id BIGINT PRIMARY KEY,
  slug TEXT UNIQUE NOT NULL,
  name TEXT NOT NULL,
  logo_url TEXT,
  industry TEXT,
  country_code TEXT DEFAULT 'VN',
  created_by BIGINT REFERENCES cosa.users(id) ON DELETE CASCADE,
  status TEXT NOT NULL DEFAULT 'active',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  deleted_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_cp_companies_slug ON cosa.companies(slug);
CREATE INDEX IF NOT EXISTS idx_cp_companies_status ON cosa.companies(status);

CREATE TABLE IF NOT EXISTS cosa.company_memberships (
  id BIGINT PRIMARY KEY,
  company_id BIGINT NOT NULL REFERENCES cosa.companies(id) ON DELETE CASCADE,
  user_id BIGINT NOT NULL REFERENCES cosa.users(id) ON DELETE CASCADE,
  role_id TEXT NOT NULL REFERENCES cosa.roles(id) DEFAULT 'user',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (company_id, user_id)
);

CREATE INDEX IF NOT EXISTS idx_cp_company_memberships_user ON cosa.company_memberships(user_id);
CREATE INDEX IF NOT EXISTS idx_cp_company_memberships_company ON cosa.company_memberships(company_id);

CREATE TABLE IF NOT EXISTS cosa.plans (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  description TEXT,
  default_limits JSONB NOT NULL DEFAULT '{"max_projects": 1, "max_seats": 2, "max_scheduled_agents": 1}',
  default_features JSONB NOT NULL DEFAULT '{"marketing": true, "crm": true, "finance": false, "custom_domain": false}',
  is_public BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

INSERT INTO cosa.plans (id, name, description) VALUES
  ('free', 'Free Plan', 'Free tier for exploration'),
  ('starter', 'Starter Plan', 'Default plan for new workspaces'),
  ('pro', 'Pro Plan', 'For growing companies'),
  ('enterprise', 'Enterprise Plan', 'For large organizations')
ON CONFLICT (id) DO NOTHING;

CREATE TABLE IF NOT EXISTS cosa.licenses (
  id BIGINT PRIMARY KEY,
  company_id BIGINT NOT NULL REFERENCES cosa.companies(id) ON DELETE CASCADE,
  plan_id TEXT NOT NULL REFERENCES cosa.plans(id),
  license_key TEXT UNIQUE NOT NULL,
  status TEXT NOT NULL DEFAULT 'active',
  starts_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  expires_at TIMESTAMPTZ,
  grace_period_days INTEGER NOT NULL DEFAULT 7,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  deleted_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS cosa.company_entitlements (
  company_id BIGINT PRIMARY KEY REFERENCES cosa.companies(id) ON DELETE CASCADE,
  plan_id TEXT NOT NULL REFERENCES cosa.plans(id),
  effective_limits JSONB NOT NULL DEFAULT '{}',
  effective_features JSONB NOT NULL DEFAULT '{}',
  custom_overrides JSONB NOT NULL DEFAULT '{}',
  last_issued_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  snapshot_signature TEXT,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS cosa.company_agent_policy (
    id BIGINT PRIMARY KEY,
    company_id BIGINT NOT NULL REFERENCES cosa.companies(id) ON DELETE CASCADE,
    tool_pattern TEXT NOT NULL,
    decision TEXT NOT NULL CHECK (decision IN ('ALLOW', 'REQUIRE_APPROVAL', 'DENY')),
    reason TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_company_agent_policy_company_id ON cosa.company_agent_policy(company_id);
CREATE UNIQUE INDEX IF NOT EXISTS idx_company_agent_policy_company_tool ON cosa.company_agent_policy(company_id, tool_pattern);
