-- Migration 9 down

DROP TABLE IF EXISTS core.business_policy_cutover_markers CASCADE;

ALTER TABLE core.workspace_policy_versions
  DROP COLUMN IF EXISTS cutover_at,
  DROP COLUMN IF EXISTS source;
