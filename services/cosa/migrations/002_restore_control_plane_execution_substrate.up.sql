-- Task 0 — Khôi phục Control Plane execution substrate bị đợt squash baseline
-- Founder Trial R1 (commit 81461673) xoá khỏi migration history NHƯNG code đang
-- chạy vẫn phụ thuộc:
--   * services/cosa/storage/control-plane-schema.ts  (workers, runtime_leases, scheduled_tasks)
--   * services/cosa/services/control-plane-scheduler.service.ts / control-plane-lease.service.ts
--     / child-scheduler.service.ts + services/cosa/control-plane.cron.ts (reclaimStuckTasks)
--   * apps/cosa/worker/main.py (plane.scheduler.* + plane.lease_client.*)
--
-- Đây là state PHẲNG cuối cùng của các migration đã xoá:
--   7_control_plane_leases_workers  + 10_scheduled_tasks_durable_claims
--   + 16_scheduled_task_child_edges + 17_scheduled_task_status_blocked
-- Schema `control_plane` đã tồn tại từ 001_founder_trial_mvp_baseline. Thuần
-- expand-only: CREATE ... IF NOT EXISTS, không DROP/ALTER cột sẵn có.
-- KHÔNG khôi phục missions/tasks/assignments/watches/trigger_policies/
-- signal_observations/delivery_*/cost_ledger (dormant, không có consumer
-- production) và workspace_execution_leases/workspace_runtime_nodes (M5/M6
-- local-vs-cloud failover, ngoài happy path dispatch).

CREATE TABLE IF NOT EXISTS control_plane.workers (
    id TEXT PRIMARY KEY,
    runtime_kind TEXT NOT NULL,
    endpoint TEXT,
    capabilities JSONB NOT NULL DEFAULT '[]'::jsonb,
    concurrency_limit INTEGER NOT NULL DEFAULT 1,
    trust_tier TEXT NOT NULL DEFAULT 'T0',
    last_heartbeat_at TIMESTAMPTZ,
    status TEXT NOT NULL DEFAULT 'online' CHECK (status IN ('online', 'offline', 'degraded')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Thay packages/agent/runs/leases.py::RunLeaseManager (in-memory) — khoá thực
-- thi phân tán chống split-brain thật giữa nhiều process. 1 run_id ≤ 1 lease.
CREATE TABLE IF NOT EXISTS control_plane.runtime_leases (
    run_id TEXT PRIMARY KEY,
    worker_id TEXT NOT NULL REFERENCES control_plane.workers(id) ON DELETE CASCADE,
    lease_token TEXT NOT NULL,
    acquired_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at TIMESTAMPTZ NOT NULL,
    heartbeat_interval_sec INTEGER NOT NULL DEFAULT 30
);

-- Thay packages/agent/coordination/scheduler.py::RunScheduler (in-memory).
-- Cột attempt_count..dead_letter_reason: Phase 3 Durable Queue Recovery
-- (claim atomic bằng fencing token claim_token + retry backoff + dead-letter).
-- Cột parent_task_id..completion_key: P1 durable hierarchical supervisor.
-- CHECK status có 'blocked' (child task chờ depends_on) — đặt tên constraint
-- tường minh để migration sau ALTER được.
CREATE TABLE IF NOT EXISTS control_plane.scheduled_tasks (
    id TEXT PRIMARY KEY,
    coalescing_key TEXT,
    target_spec_id TEXT NOT NULL,
    target_spec_kind TEXT NOT NULL DEFAULT 'agent',
    input_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    run_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    status TEXT NOT NULL DEFAULT 'scheduled',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    attempt_count INTEGER NOT NULL DEFAULT 0,
    max_attempts INTEGER NOT NULL DEFAULT 5,
    claimed_by TEXT,
    claim_token TEXT,
    claimed_at TIMESTAMPTZ,
    heartbeat_at TIMESTAMPTZ,
    visibility_timeout_at TIMESTAMPTZ,
    last_error TEXT,
    next_retry_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    dead_letter_reason TEXT,
    parent_task_id TEXT,
    child_id TEXT,
    depends_on JSONB NOT NULL DEFAULT '[]'::jsonb,
    join_policy TEXT,
    join_quorum INTEGER,
    child_result JSONB,
    completion_key TEXT,
    CONSTRAINT scheduled_tasks_status_check
        CHECK (status IN ('scheduled', 'processing', 'completed', 'coalesced', 'failed', 'blocked'))
);

-- Chỉ 1 task 'scheduled' đang chờ cho mỗi coalescing_key — khớp hành vi coalesce
-- của RunScheduler gốc.
CREATE UNIQUE INDEX IF NOT EXISTS idx_control_plane_scheduled_tasks_coalescing_key_pending
    ON control_plane.scheduled_tasks (coalescing_key)
    WHERE status = 'scheduled' AND coalescing_key IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_control_plane_scheduled_tasks_status_run_at
    ON control_plane.scheduled_tasks (status, run_at);
-- Sweeper (cron) quét đúng tập nhỏ: processing đã hết visibility timeout.
CREATE INDEX IF NOT EXISTS idx_control_plane_scheduled_tasks_visibility_timeout
    ON control_plane.scheduled_tasks (visibility_timeout_at)
    WHERE status = 'processing';
CREATE INDEX IF NOT EXISTS idx_control_plane_scheduled_tasks_next_retry
    ON control_plane.scheduled_tasks (next_retry_at)
    WHERE status = 'scheduled' AND next_retry_at IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_scheduled_tasks_parent
    ON control_plane.scheduled_tasks (parent_task_id)
    WHERE parent_task_id IS NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS uq_scheduled_tasks_parent_child
    ON control_plane.scheduled_tasks (parent_task_id, child_id)
    WHERE parent_task_id IS NOT NULL;
