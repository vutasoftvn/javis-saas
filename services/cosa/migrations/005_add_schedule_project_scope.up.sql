-- 005_add_schedule_project_scope.up.sql
--
-- Schedule Project Scope fix (docs/superpowers/specs/2026-09-14-schedule-
-- project-scope-design.md). Expand-only: nullable columns, backfilled by a
-- separate script (Task 2), not by this migration.

ALTER TABLE control_plane.workspace_schedule_definitions
  ADD COLUMN IF NOT EXISTS project_id TEXT,
  ADD COLUMN IF NOT EXISTS is_legacy_unscoped BOOLEAN NOT NULL DEFAULT false;

ALTER TABLE control_plane.workspace_schedule_executions
  ADD COLUMN IF NOT EXISTS project_id_snapshot TEXT;
