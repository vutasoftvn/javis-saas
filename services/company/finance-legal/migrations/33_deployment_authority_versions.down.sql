ALTER TABLE legal.workspace_ai_deployments
  DROP COLUMN IF EXISTS approved_version,
  DROP COLUMN IF EXISTS policy_version,
  DROP COLUMN IF EXISTS approved_by_member_id,
  DROP COLUMN IF EXISTS reviewer_member_id,
  DROP COLUMN IF EXISTS accountable_member_id,
  DROP COLUMN IF EXISTS created_by_member_id;
