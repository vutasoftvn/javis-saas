-- services/cosa/migrations/19_workspace_licenses_entitlements.up.sql
CREATE TABLE IF NOT EXISTS cosa.workspace_licenses (
  id                    BIGINT PRIMARY KEY,
  platform_workspace_id BIGINT NOT NULL REFERENCES cosa.platform_workspaces(id) ON DELETE CASCADE,
  plan_id               TEXT   NOT NULL REFERENCES cosa.plans(id),
  license_key           TEXT   NOT NULL UNIQUE,
  status                TEXT   NOT NULL DEFAULT 'active',
  starts_at             TIMESTAMPTZ NOT NULL DEFAULT now(),
  expires_at            TIMESTAMPTZ,
  grace_period_days     INTEGER NOT NULL DEFAULT 7,
  created_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
  deleted_at            TIMESTAMPTZ,
  UNIQUE (platform_workspace_id)
);

CREATE TABLE IF NOT EXISTS cosa.workspace_entitlements (
  platform_workspace_id BIGINT PRIMARY KEY REFERENCES cosa.platform_workspaces(id) ON DELETE CASCADE,
  plan_id               TEXT   NOT NULL REFERENCES cosa.plans(id),
  effective_limits      JSONB  NOT NULL DEFAULT '{}',
  effective_features    JSONB  NOT NULL DEFAULT '{}',
  custom_overrides      JSONB  NOT NULL DEFAULT '{}',
  snapshot_signature    TEXT,
  last_issued_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at            TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS cosa.platform_workspace_sync_log (
  id                    BIGINT PRIMARY KEY,
  platform_workspace_id BIGINT NOT NULL REFERENCES cosa.platform_workspaces(id) ON DELETE CASCADE,
  client_creation_id    TEXT   NOT NULL,
  sync_status           TEXT   NOT NULL DEFAULT 'pending'
                          CHECK (sync_status IN ('pending','success','failed')),
  error_msg             TEXT,
  synced_at             TIMESTAMPTZ,
  created_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (client_creation_id)
);
