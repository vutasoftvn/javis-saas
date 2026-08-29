-- services/cosa/migrations/20_backfill_platform_workspaces.up.sql
-- Idempotent backfill of legacy companies into platform_workspaces

-- 1. Insert platform_workspaces for any company not yet backfilled
INSERT INTO cosa.platform_workspaces (id, workspace_name, owner_user_id, status, created_at, updated_at)
SELECT
  c.id,
  c.name,
  c.created_by,
  'active',
  c.created_at,
  now()
FROM cosa.companies c
WHERE c.created_by IS NOT NULL
  AND NOT EXISTS (
    SELECT 1 FROM cosa.platform_workspace_sync_log log
    WHERE log.client_creation_id = 'backfill:company:' || c.id::text
  )
ON CONFLICT (id) DO NOTHING;

-- 2. Insert platform_workspace_memberships
INSERT INTO cosa.platform_workspace_memberships (id, platform_workspace_id, user_id, role, created_at, updated_at)
SELECT
  cm.id,
  cm.company_id,
  cm.user_id,
  CASE WHEN cm.role_id = 'founder' THEN 'founder' ELSE 'member' END,
  cm.created_at,
  cm.updated_at
FROM cosa.company_memberships cm
JOIN cosa.platform_workspaces pw ON pw.id = cm.company_id
ON CONFLICT (platform_workspace_id, user_id) DO NOTHING;

-- 3. Insert workspace_licenses (from existing licenses or default free)
INSERT INTO cosa.workspace_licenses (id, platform_workspace_id, plan_id, license_key, status, starts_at, expires_at, grace_period_days, created_at, updated_at)
SELECT
  l.id,
  l.company_id,
  l.plan_id,
  l.license_key,
  l.status,
  l.starts_at,
  l.expires_at,
  l.grace_period_days,
  l.created_at,
  l.updated_at
FROM cosa.licenses l
JOIN cosa.platform_workspaces pw ON pw.id = l.company_id
ON CONFLICT (platform_workspace_id) DO NOTHING;

-- Default free license for workspaces without an existing license
INSERT INTO cosa.workspace_licenses (id, platform_workspace_id, plan_id, license_key, status, starts_at, grace_period_days, created_at, updated_at)
SELECT
  pw.id,
  pw.id,
  'free',
  'wl_bk_free_' || pw.id::text,
  'active',
  pw.created_at,
  7,
  pw.created_at,
  now()
FROM cosa.platform_workspaces pw
WHERE NOT EXISTS (
  SELECT 1 FROM cosa.workspace_licenses wl WHERE wl.platform_workspace_id = pw.id
)
ON CONFLICT (platform_workspace_id) DO NOTHING;

-- 4. Insert workspace_entitlements
INSERT INTO cosa.workspace_entitlements (platform_workspace_id, plan_id, effective_limits, effective_features, custom_overrides, snapshot_signature, last_issued_at, updated_at)
SELECT
  ce.company_id,
  ce.plan_id,
  ce.effective_limits,
  ce.effective_features,
  ce.custom_overrides,
  ce.snapshot_signature,
  ce.last_issued_at,
  ce.updated_at
FROM cosa.company_entitlements ce
JOIN cosa.platform_workspaces pw ON pw.id = ce.company_id
ON CONFLICT (platform_workspace_id) DO NOTHING;

-- Default free entitlement for workspaces without existing entitlements
INSERT INTO cosa.workspace_entitlements (platform_workspace_id, plan_id, effective_limits, effective_features, custom_overrides, snapshot_signature, last_issued_at, updated_at)
SELECT
  pw.id,
  'free',
  p.default_limits,
  p.default_features,
  '{}'::jsonb,
  'sig_bk_' || pw.id::text,
  now(),
  now()
FROM cosa.platform_workspaces pw
CROSS JOIN cosa.plans p
WHERE p.id = 'free'
  AND NOT EXISTS (
    SELECT 1 FROM cosa.workspace_entitlements we WHERE we.platform_workspace_id = pw.id
  )
ON CONFLICT (platform_workspace_id) DO NOTHING;

-- 5. Record in platform_workspace_sync_log
INSERT INTO cosa.platform_workspace_sync_log (id, platform_workspace_id, client_creation_id, sync_status, created_at)
SELECT
  pw.id,
  pw.id,
  'backfill:company:' || pw.id::text,
  'pending',
  now()
FROM cosa.platform_workspaces pw
JOIN cosa.companies c ON c.id = pw.id
ON CONFLICT (client_creation_id) DO NOTHING;
