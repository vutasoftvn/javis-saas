-- 003_restore_upsert_constraints.up.sql
--
-- Startup Core Task-2 reconciliation: the clean-slate 001 operations baseline
-- dropped three uniqueness constraints that service upserts (ON CONFLICT) rely
-- on, so every code path through them fails with 42P10 "no unique or exclusion
-- constraint matching the ON CONFLICT specification":
--
--   * operating.workspace_execution_settings — Drizzle marks workspace_id as
--     the primary key; 001 created the table with none.
--   * operating.workspace_capability_policy — Drizzle declares a composite PK
--     (workspace_id, capability_id); 001 created the table with none.
--   * operating.weekly_plans — weekly-goal.service upserts on (cycle_id,
--     week_no); 001 only has the 4-column partial index
--     uix_weekly_plans_cycle_week, which cannot serve as an ON CONFLICT arbiter
--     for that 2-column target. Restores the original plain unique.
--
-- Expand-only, idempotent.

DO $$ BEGIN
  ALTER TABLE ONLY operating.workspace_execution_settings
    ADD CONSTRAINT workspace_execution_settings_pkey PRIMARY KEY (workspace_id);
EXCEPTION WHEN duplicate_table THEN NULL; WHEN duplicate_object THEN NULL; WHEN invalid_table_definition THEN NULL; END $$;

DO $$ BEGIN
  ALTER TABLE ONLY operating.workspace_capability_policy
    ADD CONSTRAINT workspace_capability_policy_pkey PRIMARY KEY (workspace_id, capability_id);
EXCEPTION WHEN duplicate_table THEN NULL; WHEN duplicate_object THEN NULL; WHEN invalid_table_definition THEN NULL; END $$;

CREATE UNIQUE INDEX IF NOT EXISTS uix_weekly_plan_cycle_week
  ON operating.weekly_plans (cycle_id, week_no);
