-- 004_restore_execution_plan_constraints.up.sql
--
-- Startup Core Task-2 reconciliation: the clean-slate 001 operations baseline
-- created operating.execution_plans without the project_id FK and without the
-- one-draft-per-weekly-plan partial unique that the original 37_execution_plans
-- migration defined and that execution-plan-schema tests assert. Restores both.
-- Expand-only, idempotent.

DO $$ BEGIN
  ALTER TABLE ONLY operating.execution_plans
    ADD CONSTRAINT fk_execution_plans_project
    FOREIGN KEY (project_id) REFERENCES strategy.projects(id) ON DELETE CASCADE;
EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; WHEN invalid_table_definition THEN NULL; END $$;

CREATE UNIQUE INDEX IF NOT EXISTS uix_execution_plans_one_draft_per_weekly_plan
  ON operating.execution_plans (weekly_plan_id)
  WHERE status = 'draft' AND deleted_at IS NULL;
