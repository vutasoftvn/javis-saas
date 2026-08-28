-- P1 Task 7: child task đang chờ depends_on hoàn tất mang status 'blocked'.
-- Migration 7 chỉ cho scheduled/processing/completed/coalesced/failed.
ALTER TABLE control_plane.scheduled_tasks
  DROP CONSTRAINT IF EXISTS scheduled_tasks_status_check;
ALTER TABLE control_plane.scheduled_tasks
  ADD CONSTRAINT scheduled_tasks_status_check
  CHECK (status IN ('scheduled', 'processing', 'completed', 'coalesced', 'failed', 'blocked'));
