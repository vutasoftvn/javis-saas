-- Phase 3 (Durable Queue Recovery) —
-- docs/implementation/production-runtime-closure.md §7. `scheduled_tasks`
-- trước đây chỉ có status='processing' không có claim/lease/sweeper fields —
-- worker chết giữa chừng làm task kẹt vĩnh viễn ở 'processing', không ai
-- reclaim được. Thêm đúng field cần cho claim atomic (fencing token) +
-- retry với backoff + dead-letter khi vượt max_attempts.

ALTER TABLE control_plane.scheduled_tasks
    ADD COLUMN attempt_count INTEGER NOT NULL DEFAULT 0,
    ADD COLUMN max_attempts INTEGER NOT NULL DEFAULT 5,
    ADD COLUMN claimed_by TEXT,
    ADD COLUMN claim_token TEXT,
    ADD COLUMN claimed_at TIMESTAMPTZ,
    ADD COLUMN heartbeat_at TIMESTAMPTZ,
    ADD COLUMN visibility_timeout_at TIMESTAMPTZ,
    ADD COLUMN last_error TEXT,
    ADD COLUMN next_retry_at TIMESTAMPTZ,
    ADD COLUMN completed_at TIMESTAMPTZ,
    ADD COLUMN dead_letter_reason TEXT;

-- Sweeper (cron) quét đúng tập nhỏ: processing đã hết visibility timeout.
CREATE INDEX idx_control_plane_scheduled_tasks_visibility_timeout
    ON control_plane.scheduled_tasks (visibility_timeout_at)
    WHERE status = 'processing';

-- Poll due tasks cho worker: scheduled với run_at <= now, kể cả task vừa bị
-- reclaim (next_retry_at đã ghi vào run_at khi reclaim, xem service).
CREATE INDEX idx_control_plane_scheduled_tasks_next_retry
    ON control_plane.scheduled_tasks (next_retry_at)
    WHERE status = 'scheduled' AND next_retry_at IS NOT NULL;
