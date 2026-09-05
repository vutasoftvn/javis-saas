-- Migration 33: Add workforce authority and policy versioning columns to AI deployments
ALTER TABLE legal.workspace_ai_deployments
  ADD COLUMN IF NOT EXISTS created_by_member_id BIGINT,
  ADD COLUMN IF NOT EXISTS accountable_member_id BIGINT,
  ADD COLUMN IF NOT EXISTS reviewer_member_id BIGINT,
  ADD COLUMN IF NOT EXISTS approved_by_member_id BIGINT,
  ADD COLUMN IF NOT EXISTS policy_version INTEGER NOT NULL DEFAULT 1,
  ADD COLUMN IF NOT EXISTS approved_version INTEGER;

-- Backfill created_by_member_id and accountable_member_id from founder_member_id
UPDATE legal.workspace_ai_deployments
SET created_by_member_id = founder_member_id
WHERE created_by_member_id IS NULL;

UPDATE legal.workspace_ai_deployments
SET accountable_member_id = founder_member_id
WHERE accountable_member_id IS NULL;
