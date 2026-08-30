-- Durable retry bookkeeping for workspace_schedule_executions: track how many
-- enqueue attempts a queued occurrence has consumed and when it may be
-- retried next, so the dispatcher can claim due retries deterministically
-- (instead of retrying every tick or losing count across process restarts)
-- and so a retry loop terminates into 'enqueue_failed' after a bounded
-- number of attempts instead of stranding the occurrence forever.

ALTER TABLE control_plane.workspace_schedule_executions
    ADD COLUMN IF NOT EXISTS attempt_count integer NOT NULL DEFAULT 0;

ALTER TABLE control_plane.workspace_schedule_executions
    ADD COLUMN IF NOT EXISTS next_attempt_at timestamptz;
