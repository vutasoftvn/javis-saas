-- Rollback for 034_automation_plan_proposal_decision.up.sql
ALTER TABLE operating.automation_plan_proposals
  DROP COLUMN IF EXISTS decided_by_member_id,
  DROP COLUMN IF EXISTS decided_by_user_id;
