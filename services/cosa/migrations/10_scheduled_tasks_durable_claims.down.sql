-- Rollback 10_scheduled_tasks_durable_claims.up.sql
DROP INDEX IF EXISTS control_plane.idx_control_plane_scheduled_tasks_next_retry;
DROP INDEX IF EXISTS control_plane.idx_control_plane_scheduled_tasks_visibility_timeout;

ALTER TABLE control_plane.scheduled_tasks
    DROP COLUMN IF EXISTS dead_letter_reason,
    DROP COLUMN IF EXISTS completed_at,
    DROP COLUMN IF EXISTS next_retry_at,
    DROP COLUMN IF EXISTS last_error,
    DROP COLUMN IF EXISTS visibility_timeout_at,
    DROP COLUMN IF EXISTS heartbeat_at,
    DROP COLUMN IF EXISTS claimed_at,
    DROP COLUMN IF EXISTS claim_token,
    DROP COLUMN IF EXISTS claimed_by,
    DROP COLUMN IF EXISTS max_attempts,
    DROP COLUMN IF EXISTS attempt_count;
