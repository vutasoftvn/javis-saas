-- Rollback for 003_restore_upsert_constraints.up.sql
DROP INDEX IF EXISTS operating.uix_weekly_plan_cycle_week;
ALTER TABLE IF EXISTS operating.workspace_capability_policy DROP CONSTRAINT IF EXISTS workspace_capability_policy_pkey;
ALTER TABLE IF EXISTS operating.workspace_execution_settings DROP CONSTRAINT IF EXISTS workspace_execution_settings_pkey;
