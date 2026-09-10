-- Rollback for 004_restore_execution_plan_constraints.up.sql
DROP INDEX IF EXISTS operating.uix_execution_plans_one_draft_per_weekly_plan;
ALTER TABLE IF EXISTS operating.execution_plans DROP CONSTRAINT IF EXISTS fk_execution_plans_project;
