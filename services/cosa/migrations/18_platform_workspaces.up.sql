-- services/cosa/migrations/18_platform_workspaces.up.sql
-- Lớp tenant sản phẩm ("Venture Workspace") tách khỏi pháp nhân legacy `companies`.
-- Level 0: một cá nhân tạo workspace trước khi có công ty đăng ký.
CREATE TABLE IF NOT EXISTS cosa.platform_workspaces (
  id             BIGINT PRIMARY KEY,
  workspace_name TEXT        NOT NULL,
  owner_user_id  BIGINT      NOT NULL REFERENCES cosa.users(id) ON DELETE CASCADE,
  status         TEXT        NOT NULL DEFAULT 'active'
                   CHECK (status IN ('active','archived')),
  created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_platform_workspaces_owner
  ON cosa.platform_workspaces(owner_user_id);

CREATE TABLE IF NOT EXISTS cosa.platform_workspace_memberships (
  id                    BIGINT PRIMARY KEY,
  platform_workspace_id BIGINT NOT NULL REFERENCES cosa.platform_workspaces(id) ON DELETE CASCADE,
  user_id               BIGINT NOT NULL REFERENCES cosa.users(id) ON DELETE CASCADE,
  role                  TEXT   NOT NULL DEFAULT 'member'
                          CHECK (role IN ('founder','member','viewer')),
  created_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (platform_workspace_id, user_id)
);
