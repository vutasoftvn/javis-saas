-- Wave 7 — Port packages/agent_core/runs/leases.py (RunLeaseManager) và
-- packages/agent_core/coordination/scheduler.py (RunScheduler) sang durable
-- Postgres (ADR-CONTROLPLANE-001 §2). 2 class Python gốc hoàn toàn in-memory
-- (dict + asyncio.Lock), không chống split-brain thật giữa nhiều process.

CREATE TABLE control_plane.workers (
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

-- Thay RunLeaseManager (packages/agent_core/runs/leases.py) — khoá thực thi
-- phân tán chống split-brain THẬT giữa nhiều process, không chỉ 1 asyncio.Lock
-- trong 1 process. 1 run_id chỉ có tối đa 1 lease đang hiệu lực.
CREATE TABLE control_plane.runtime_leases (
    run_id TEXT PRIMARY KEY,
    worker_id TEXT NOT NULL REFERENCES control_plane.workers(id) ON DELETE CASCADE,
    lease_token TEXT NOT NULL,
    acquired_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at TIMESTAMPTZ NOT NULL,
    heartbeat_interval_sec INTEGER NOT NULL DEFAULT 30
);

-- Thay RunScheduler (packages/agent_core/coordination/scheduler.py) —
-- coalescing work queue durable. `coalescing_key` NULL nghĩa là không coalesce.
CREATE TABLE control_plane.scheduled_tasks (
    id TEXT PRIMARY KEY,
    coalescing_key TEXT,
    target_spec_id TEXT NOT NULL,
    target_spec_kind TEXT NOT NULL DEFAULT 'agent',
    input_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    run_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    status TEXT NOT NULL DEFAULT 'scheduled' CHECK (status IN ('scheduled', 'processing', 'completed', 'coalesced', 'failed')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Chỉ 1 task 'scheduled' đang chờ cho mỗi coalescing_key tại 1 thời điểm — khớp
-- đúng hành vi coalesce của RunScheduler gốc (gộp payload vào task đang chờ).
CREATE UNIQUE INDEX idx_control_plane_scheduled_tasks_coalescing_key_pending
    ON control_plane.scheduled_tasks(coalescing_key) WHERE status = 'scheduled' AND coalescing_key IS NOT NULL;
CREATE INDEX idx_control_plane_scheduled_tasks_status_run_at ON control_plane.scheduled_tasks(status, run_at);
