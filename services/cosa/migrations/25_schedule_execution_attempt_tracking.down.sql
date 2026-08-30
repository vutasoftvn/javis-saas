ALTER TABLE control_plane.workspace_schedule_executions
    DROP COLUMN IF EXISTS next_attempt_at;

ALTER TABLE control_plane.workspace_schedule_executions
    DROP COLUMN IF EXISTS attempt_count;
