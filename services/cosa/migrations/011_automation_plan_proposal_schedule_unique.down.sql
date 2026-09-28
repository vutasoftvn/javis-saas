-- Rollback for 011_automation_plan_proposal_schedule_unique.up.sql
DROP INDEX IF EXISTS control_plane.uq_organization_schedule_definitions_proposal;

CREATE INDEX IF NOT EXISTS idx_organization_schedule_definitions_proposal
  ON control_plane.organization_schedule_definitions (automation_plan_proposal_id)
  WHERE automation_plan_proposal_id IS NOT NULL;
