-- BASELINE CANDIDATE -- NEW_CANONICAL_DRAFT (isolated verification only, not runtime-verified,
-- not PROMOTED/RETIRE -- see ADR-CONTROLPLANE-001, status ACCEPTED but 'triển khai chưa bắt đầu')
-- Domain: services/cosa -- control_plane schema (Wave 7, migrations 6-9, verbatim, no known issue)

-- source: services/cosa/migrations/6_control_plane_missions_tasks.up.sql
-- Wave 7 — Control Plane (ADR-CONTROLPLANE-001, DRAFT chưa review; Blueprint V2 §39/§71).
-- KHÔNG có consumer production hiện tại — hạ tầng đón đầu theo yêu cầu người
-- dùng, chưa verify được bằng Encore CLI/Postgres thật trong môi trường này.
CREATE SCHEMA IF NOT EXISTS control_plane;

CREATE TABLE control_plane.missions (
    id BIGINT PRIMARY KEY,
    tenant_id BIGINT NOT NULL,
    creator_id BIGINT NOT NULL,
    goal TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'completed', 'failed', 'cancelled')),
    priority INTEGER NOT NULL DEFAULT 0,
    budget_cents BIGINT,
    deadline TIMESTAMPTZ,
    root_run_id TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at TIMESTAMPTZ
);

CREATE INDEX idx_control_plane_missions_tenant_status ON control_plane.missions(tenant_id, status);

CREATE TABLE control_plane.tasks (
    id BIGINT PRIMARY KEY,
    mission_id BIGINT NOT NULL REFERENCES control_plane.missions(id) ON DELETE CASCADE,
    parent_task_id BIGINT REFERENCES control_plane.tasks(id) ON DELETE CASCADE,
    description TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'assigned', 'running', 'completed', 'failed', 'cancelled')),
    priority INTEGER NOT NULL DEFAULT 0,
    requirements JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_control_plane_tasks_mission ON control_plane.tasks(mission_id);
CREATE INDEX idx_control_plane_tasks_status ON control_plane.tasks(status);

CREATE TABLE control_plane.assignments (
    id BIGINT PRIMARY KEY,
    task_id BIGINT NOT NULL REFERENCES control_plane.tasks(id) ON DELETE CASCADE,
    worker_id TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'leased' CHECK (status IN ('leased', 'completed', 'failed', 'released')),
    lease_until TIMESTAMPTZ NOT NULL,
    attempt_no INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Atomic checkout: 1 task chỉ có tối đa 1 assignment đang "leased" tại 1 thời điểm.
CREATE UNIQUE INDEX idx_control_plane_assignments_task_active_lease
    ON control_plane.assignments(task_id) WHERE status = 'leased';
CREATE INDEX idx_control_plane_assignments_worker ON control_plane.assignments(worker_id);

-- source: services/cosa/migrations/7_control_plane_leases_workers.up.sql
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

-- source: services/cosa/migrations/8_control_plane_watches_signals.up.sql
-- Wave 7 — Watch/Signal/Trigger cho proactive agent (Blueprint V2 §71.1).
CREATE TABLE control_plane.watches (
    id BIGINT PRIMARY KEY,
    tenant_id BIGINT NOT NULL,
    kind TEXT NOT NULL,
    config JSONB NOT NULL DEFAULT '{}'::jsonb,
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'paused', 'retired')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_control_plane_watches_tenant ON control_plane.watches(tenant_id, status);

CREATE TABLE control_plane.trigger_policies (
    id BIGINT PRIMARY KEY,
    watch_id BIGINT NOT NULL REFERENCES control_plane.watches(id) ON DELETE CASCADE,
    condition JSONB NOT NULL DEFAULT '{}'::jsonb,
    target_agent_spec_id TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_control_plane_trigger_policies_watch ON control_plane.trigger_policies(watch_id);

-- `dedupe_key` chống duplicate proactive Run cho cùng 1 signal thật (Blueprint
-- V2 Scenario G: "Duplicate signal không tạo duplicate proactive Run/delivery").
CREATE TABLE control_plane.signal_observations (
    id BIGINT PRIMARY KEY,
    watch_id BIGINT NOT NULL REFERENCES control_plane.watches(id) ON DELETE CASCADE,
    dedupe_key TEXT NOT NULL,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    triggered_run_id TEXT,
    observed_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX idx_control_plane_signal_observations_dedupe
    ON control_plane.signal_observations(watch_id, dedupe_key);

-- source: services/cosa/migrations/9_control_plane_delivery.up.sql
-- Wave 7 — Delivery policy + cost ledger (Blueprint V2 §71.1, §28).
CREATE TABLE control_plane.delivery_policies (
    id BIGINT PRIMARY KEY,
    tenant_id BIGINT NOT NULL,
    channel TEXT NOT NULL CHECK (channel IN ('flutter', 'email', 'slack', 'webhook')),
    config JSONB NOT NULL DEFAULT '{}'::jsonb,
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'paused')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_control_plane_delivery_policies_tenant ON control_plane.delivery_policies(tenant_id);

CREATE TABLE control_plane.delivery_attempts (
    id BIGINT PRIMARY KEY,
    delivery_policy_id BIGINT NOT NULL REFERENCES control_plane.delivery_policies(id) ON DELETE CASCADE,
    artifact_ref TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'sent', 'failed')),
    error_message TEXT,
    attempted_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_control_plane_delivery_attempts_policy ON control_plane.delivery_attempts(delivery_policy_id);

CREATE TABLE control_plane.cost_ledger (
    id BIGINT PRIMARY KEY,
    tenant_id BIGINT NOT NULL,
    mission_id BIGINT REFERENCES control_plane.missions(id) ON DELETE SET NULL,
    run_id TEXT,
    provider TEXT NOT NULL,
    model TEXT NOT NULL,
    input_tokens BIGINT NOT NULL DEFAULT 0,
    output_tokens BIGINT NOT NULL DEFAULT 0,
    cost_cents BIGINT NOT NULL DEFAULT 0,
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_control_plane_cost_ledger_tenant ON control_plane.cost_ledger(tenant_id, recorded_at);
CREATE INDEX idx_control_plane_cost_ledger_mission ON control_plane.cost_ledger(mission_id);

