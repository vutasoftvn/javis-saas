-- Rollback for 010_automation_plan_schedule_pre_authorization.up.sql
DROP INDEX IF EXISTS control_plane.idx_organization_schedule_definitions_proposal;

ALTER TABLE control_plane.organization_schedule_executions
  DROP COLUMN IF EXISTS pre_authorized_capability_ids_snapshot,
  DROP COLUMN IF EXISTS founder_member_id_snapshot,
  DROP COLUMN IF EXISTS founder_user_id_snapshot,
  DROP COLUMN IF EXISTS token_budget_per_run_snapshot;

ALTER TABLE control_plane.organization_schedule_definitions
  DROP COLUMN IF EXISTS pre_authorized_capability_ids,
  DROP COLUMN IF EXISTS founder_member_id,
  DROP COLUMN IF EXISTS founder_user_id,
  DROP COLUMN IF EXISTS automation_plan_proposal_id,
  DROP COLUMN IF EXISTS token_budget_per_run;
