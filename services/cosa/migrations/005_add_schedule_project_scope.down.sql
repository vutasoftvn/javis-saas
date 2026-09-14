-- 005_add_schedule_project_scope.down.sql
ALTER TABLE control_plane.workspace_schedule_executions
  DROP COLUMN IF EXISTS project_id_snapshot;

ALTER TABLE control_plane.workspace_schedule_definitions
  DROP COLUMN IF EXISTS is_legacy_unscoped,
  DROP COLUMN IF EXISTS project_id;
