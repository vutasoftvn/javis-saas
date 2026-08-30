-- Update check constraint for workspace_schedule_executions to include enqueue_retry and enqueue_failed states

ALTER TABLE control_plane.workspace_schedule_executions
    DROP CONSTRAINT IF EXISTS chk_schedule_execution_state;

ALTER TABLE control_plane.workspace_schedule_executions
    ADD CONSTRAINT chk_schedule_execution_state
    CHECK (state IN ('queued', 'enqueue_retry', 'enqueue_failed', 'running', 'succeeded', 'failed', 'blocked_reauth', 'cancelled'));
