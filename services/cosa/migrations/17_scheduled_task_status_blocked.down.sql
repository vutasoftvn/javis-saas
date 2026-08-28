-- Rollback 17_scheduled_task_status_blocked.up.sql
ALTER TABLE control_plane.scheduled_tasks
  DROP CONSTRAINT IF EXISTS scheduled_tasks_status_check;

ALTER TABLE control_plane.scheduled_tasks
  ADD CONSTRAINT scheduled_tasks_status_check
  CHECK (status IN ('scheduled', 'processing', 'completed', 'coalesced', 'failed'));
