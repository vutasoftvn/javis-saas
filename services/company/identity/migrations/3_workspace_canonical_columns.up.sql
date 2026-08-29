-- services/company/identity/migrations/3_workspace_canonical_columns.up.sql
-- M2 §1 — cột canonical cho Workspace aggregate: slug, status, runtime/sync mode,
-- stage_version (M4 dùng), primary_legal_entity_id, archived_at.
-- Enum khớp shared/contracts/enums.json (M0). company_stage/venture_stage_entered_at
-- giữ tạm cho M4 backfill.
ALTER TABLE core.workspaces
  ADD COLUMN IF NOT EXISTS slug TEXT,
  ADD COLUMN IF NOT EXISTS status TEXT NOT NULL DEFAULT 'ACTIVE',
  ADD COLUMN IF NOT EXISTS stage_version INTEGER NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS runtime_mode TEXT NOT NULL DEFAULT 'LOCAL_ONLY',
  ADD COLUMN IF NOT EXISTS sync_policy TEXT NOT NULL DEFAULT 'CONTROL_METADATA_ONLY',
  ADD COLUMN IF NOT EXISTS sync_status TEXT NOT NULL DEFAULT 'LOCAL_ONLY',
  ADD COLUMN IF NOT EXISTS primary_legal_entity_id BIGINT,
  ADD COLUMN IF NOT EXISTS archived_at TIMESTAMPTZ;

ALTER TABLE core.workspaces
  ADD CONSTRAINT workspaces_status_chk
    CHECK (status IN ('ACTIVE', 'ARCHIVED', 'SUSPENDED')),
  ADD CONSTRAINT workspaces_runtime_mode_chk
    CHECK (runtime_mode IN ('LOCAL_ONLY', 'REMOTE_ACCESS', 'CLOUD_CONTINUITY')),
  ADD CONSTRAINT workspaces_sync_policy_chk
    CHECK (sync_policy IN ('CONTROL_METADATA_ONLY', 'SELECTIVE_ENCRYPTED', 'FULL_ENCRYPTED')),
  ADD CONSTRAINT workspaces_sync_status_chk
    CHECK (sync_status IN ('LOCAL_ONLY', 'PENDING', 'IN_SYNC', 'CONFLICT', 'ERROR'));

-- slug là DNS identity toàn cầu khi link platform (nullable khi local-only chưa link).
CREATE UNIQUE INDEX IF NOT EXISTS uq_workspaces_slug
  ON core.workspaces (slug) WHERE slug IS NOT NULL;
