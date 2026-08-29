-- Revert M4 §2.

ALTER TABLE strategy.workspace_stage_transitions
  DROP CONSTRAINT IF EXISTS workspace_stage_transitions_source_chk;

ALTER TABLE strategy.workspace_stage_transitions
  DROP COLUMN IF EXISTS stage_version_from,
  DROP COLUMN IF EXISTS source,
  DROP COLUMN IF EXISTS actor_role,
  DROP COLUMN IF EXISTS policy_version,
  DROP COLUMN IF EXISTS override_approval_ref,
  DROP COLUMN IF EXISTS evidence_snapshot,
  DROP COLUMN IF EXISTS evaluation_result;

ALTER TABLE strategy.stage_transition_policies
  DROP COLUMN IF EXISTS policy_version;
