-- Migration 9: Add business policy sources, provenance metadata and cutover markers

ALTER TABLE core.workspace_policy_versions
  ADD COLUMN IF NOT EXISTS source TEXT NOT NULL DEFAULT 'native',
  ADD COLUMN IF NOT EXISTS cutover_at TIMESTAMPTZ;

CREATE TABLE IF NOT EXISTS core.business_policy_cutover_markers (
  workspace_id          BIGINT PRIMARY KEY REFERENCES core.workspaces(id) ON DELETE CASCADE,
  cutover_completed     BOOLEAN NOT NULL DEFAULT false,
  cutover_at            TIMESTAMPTZ,
  migrated_rule_count   INTEGER NOT NULL DEFAULT 0,
  needs_review_count    INTEGER NOT NULL DEFAULT 0,
  updated_at            TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
