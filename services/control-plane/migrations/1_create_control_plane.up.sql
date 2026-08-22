CREATE SCHEMA IF NOT EXISTS control_plane;

CREATE TABLE control_plane.roles (
  id TEXT PRIMARY KEY,
  scope TEXT NOT NULL,
  level INTEGER NOT NULL,
  description TEXT
);

INSERT INTO control_plane.roles (id, scope, level, description) VALUES
  ('superadmin', 'platform', 100, 'Super Administrator'),
  ('admin', 'platform', 80, 'Platform Administrator'),
  ('support', 'platform', 50, 'Support Specialist'),
  ('founder', 'company', 90, 'Company Founder / Owner'),
  ('co-founder', 'company', 80, 'Company Co-founder'),
  ('user', 'company', 10, 'Regular Member')
ON CONFLICT (id) DO NOTHING;

CREATE TABLE control_plane.users (
  id BIGSERIAL PRIMARY KEY,
  email TEXT UNIQUE,
  phone TEXT UNIQUE,
  hashed_password TEXT NOT NULL,
  is_platform_admin BOOLEAN NOT NULL DEFAULT FALSE,
  platform_role_id TEXT REFERENCES control_plane.roles(id),
  status TEXT NOT NULL DEFAULT 'active',
  last_login_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_cp_users_email ON control_plane.users(email);
CREATE INDEX idx_cp_users_phone ON control_plane.users(phone);

CREATE TABLE control_plane.profiles (
  user_id BIGINT PRIMARY KEY REFERENCES control_plane.users(id) ON DELETE CASCADE,
  full_name TEXT,
  avatar_url TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE control_plane.companies (
  id BIGSERIAL PRIMARY KEY,
  slug TEXT UNIQUE NOT NULL,
  name TEXT NOT NULL,
  logo_url TEXT,
  industry TEXT,
  country_code TEXT DEFAULT 'VN',
  created_by BIGINT REFERENCES control_plane.users(id),
  status TEXT NOT NULL DEFAULT 'active',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  deleted_at TIMESTAMPTZ
);

CREATE INDEX idx_cp_companies_slug ON control_plane.companies(slug);
CREATE INDEX idx_cp_companies_status ON control_plane.companies(status);

CREATE TABLE control_plane.company_roles (
  id BIGSERIAL PRIMARY KEY,
  company_id BIGINT NOT NULL REFERENCES control_plane.companies(id) ON DELETE CASCADE,
  user_id BIGINT NOT NULL REFERENCES control_plane.users(id) ON DELETE CASCADE,
  role_id TEXT NOT NULL REFERENCES control_plane.roles(id) DEFAULT 'user',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (company_id, user_id)
);

CREATE INDEX idx_cp_company_roles_user ON control_plane.company_roles(user_id);
CREATE INDEX idx_cp_company_roles_company ON control_plane.company_roles(company_id);

CREATE TABLE control_plane.plans (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  description TEXT,
  default_limits JSONB NOT NULL DEFAULT '{"max_projects": 1, "max_seats": 2, "max_scheduled_agents": 1}',
  default_features JSONB NOT NULL DEFAULT '{"marketing": true, "crm": true, "finance": false, "custom_domain": false}',
  is_public BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

INSERT INTO control_plane.plans (id, name, description) VALUES
  ('starter', 'Starter Plan', 'Default plan for new workspaces')
ON CONFLICT (id) DO NOTHING;

CREATE TABLE control_plane.licenses (
  id BIGSERIAL PRIMARY KEY,
  company_id BIGINT NOT NULL REFERENCES control_plane.companies(id) ON DELETE CASCADE,
  plan_id TEXT NOT NULL REFERENCES control_plane.plans(id),
  license_key TEXT UNIQUE NOT NULL,
  status TEXT NOT NULL DEFAULT 'active',
  starts_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  expires_at TIMESTAMPTZ,
  grace_period_days INTEGER NOT NULL DEFAULT 7,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE control_plane.company_entitlements (
  company_id BIGINT PRIMARY KEY REFERENCES control_plane.companies(id) ON DELETE CASCADE,
  plan_id TEXT NOT NULL REFERENCES control_plane.plans(id),
  effective_limits JSONB NOT NULL DEFAULT '{}',
  effective_features JSONB NOT NULL DEFAULT '{}',
  custom_overrides JSONB NOT NULL DEFAULT '{}',
  last_issued_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  snapshot_signature TEXT,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
