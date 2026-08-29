-- services/company/identity/migrations/3_workspace_canonical_columns.down.sql
DROP INDEX IF EXISTS core.uq_workspaces_slug;
ALTER TABLE core.workspaces
  DROP CONSTRAINT IF EXISTS workspaces_status_chk,
  DROP CONSTRAINT IF EXISTS workspaces_runtime_mode_chk,
  DROP CONSTRAINT IF EXISTS workspaces_sync_policy_chk,
  DROP CONSTRAINT IF EXISTS workspaces_sync_status_chk;
ALTER TABLE core.workspaces
  DROP COLUMN IF EXISTS slug,
  DROP COLUMN IF EXISTS status,
  DROP COLUMN IF EXISTS stage_version,
  DROP COLUMN IF EXISTS runtime_mode,
  DROP COLUMN IF EXISTS sync_policy,
  DROP COLUMN IF EXISTS sync_status,
  DROP COLUMN IF EXISTS primary_legal_entity_id,
  DROP COLUMN IF EXISTS archived_at;
