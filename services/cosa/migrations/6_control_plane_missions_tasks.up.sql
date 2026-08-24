-- Wave 7 — Control Plane (ADR-CONTROLPLANE-001, ACCEPTED — implementation
-- chưa bắt đầu, chưa có Encore endpoint consumer; Blueprint V2 §39/§71).
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
