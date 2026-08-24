-- BASELINE CANDIDATE (isolated verification only, NOT a production migration path)
-- Domain: services/cosa -- tenant/identity/commercial (cosa schema)
-- Curated subset of REAL migration files: 1,2,3,4.
-- SKIPPED: 5_rename_company_roles.up.sql (RENAME cosa.company_roles -> company_memberships
--   -- migration 1 already creates cosa.company_memberships directly under the final name;
--   cosa.company_roles never exists. Confirmed FAIL live against a throwaway Postgres.
--   This is the BLOCKER documented in LEGACY_TO_CANONICAL_SCHEMA_RECONCILIATION.md mục 4.)

-- source: services/cosa/migrations/1_create_control_plane.up.sql
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
  ('user', 'company', 10, 'Regular Member')
ON CONFLICT (id) DO NOTHING;

CREATE TABLE IF NOT EXISTS cosa.users (
  id BIGSERIAL PRIMARY KEY,
  email TEXT UNIQUE,
  phone TEXT UNIQUE,
  hashed_password TEXT NOT NULL,
  is_platform_admin BOOLEAN NOT NULL DEFAULT FALSE,
  platform_role_id TEXT REFERENCES cosa.roles(id),
  status TEXT NOT NULL DEFAULT 'active',
  last_login_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  deleted_at TIMESTAMPTZ
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
  id BIGSERIAL PRIMARY KEY,
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
  id BIGSERIAL PRIMARY KEY,
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
  ('starter', 'Starter Plan', 'Default plan for new workspaces')
ON CONFLICT (id) DO NOTHING;

CREATE TABLE IF NOT EXISTS cosa.licenses (
  id BIGSERIAL PRIMARY KEY,
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

-- source: services/cosa/migrations/2_align_schema.up.sql
ALTER TABLE IF EXISTS cosa.users ADD COLUMN IF NOT EXISTS is_platform_admin BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE IF EXISTS cosa.users ADD COLUMN IF NOT EXISTS platform_role_id TEXT;
ALTER TABLE IF EXISTS cosa.users ADD COLUMN IF NOT EXISTS status TEXT NOT NULL DEFAULT 'active';
ALTER TABLE IF EXISTS cosa.users ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT now();
ALTER TABLE IF EXISTS cosa.users ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT now();
ALTER TABLE IF EXISTS cosa.users ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ;

ALTER TABLE IF EXISTS cosa.companies ADD COLUMN IF NOT EXISTS industry TEXT;
ALTER TABLE IF EXISTS cosa.companies ADD COLUMN IF NOT EXISTS country_code TEXT DEFAULT 'VN';
ALTER TABLE IF EXISTS cosa.companies ADD COLUMN IF NOT EXISTS status TEXT NOT NULL DEFAULT 'active';
ALTER TABLE IF EXISTS cosa.companies ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT now();
ALTER TABLE IF EXISTS cosa.companies ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT now();
ALTER TABLE IF EXISTS cosa.companies ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ;

ALTER TABLE IF EXISTS cosa.licenses ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ;

-- source: services/cosa/migrations/3_add_auditor_role.up.sql
INSERT INTO cosa.roles (id, scope, level, description)
VALUES ('auditor', 'company', 20, 'Read-only company auditor')
ON CONFLICT (id) DO NOTHING;

-- source: services/cosa/migrations/4_add_agent_policy.up.sql
CREATE TABLE cosa.company_agent_policy (
    id BIGINT PRIMARY KEY,
    company_id BIGINT NOT NULL REFERENCES cosa.companies(id) ON DELETE CASCADE,
    tool_pattern TEXT NOT NULL,
    decision TEXT NOT NULL CHECK (decision IN ('ALLOW', 'REQUIRE_APPROVAL', 'DENY')),
    reason TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_company_agent_policy_company_id ON cosa.company_agent_policy(company_id);
CREATE UNIQUE INDEX idx_company_agent_policy_company_tool ON cosa.company_agent_policy(company_id, tool_pattern);

