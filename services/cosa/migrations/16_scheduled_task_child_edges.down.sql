-- Rollback 16_scheduled_task_child_edges.up.sql
DROP INDEX IF EXISTS control_plane.uq_scheduled_tasks_parent_child;
DROP INDEX IF EXISTS control_plane.idx_scheduled_tasks_parent;

ALTER TABLE control_plane.scheduled_tasks
  DROP COLUMN IF EXISTS completion_key,
  DROP COLUMN IF EXISTS child_result,
  DROP COLUMN IF EXISTS join_quorum,
  DROP COLUMN IF EXISTS join_policy,
  DROP COLUMN IF EXISTS depends_on,
  DROP COLUMN IF EXISTS child_id,
  DROP COLUMN IF EXISTS parent_task_id;
