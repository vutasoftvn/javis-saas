-- 002_restore_control_plane_dormant_tables.up.sql
--
-- Startup Core Task-2 reconciliation (control plane). The clean-slate 001
-- baseline squash dropped control_plane.{missions,tasks,assignments,watches,
-- signal_observations,trigger_policies,delivery_policies,delivery_attempts,
-- cost_ledger} and control_plane.automation_dispatches, but the registered
-- Encore endpoints + services (control-plane-mission/-delivery/-watch,
-- automation-dispatch) and their tests still use them. Replays, verbatim, the
-- pre-squash migrations 6/8/9 (Wave 7) + 003_cosa_automation_mvp. Expand-only,
-- idempotent (CREATE ... IF NOT EXISTS).

-- ============================================================================
-- from services/cosa/migrations/6_control_plane_missions_tasks.up.sql
-- ============================================================================
-- Wave 7 — Control Plane (ADR-CONTROLPLANE-001, ACCEPTED — implementation
-- chưa bắt đầu, chưa có Encore endpoint consumer; Blueprint V2 §39/§71).
-- KHÔNG có consumer production hiện tại — hạ tầng đón đầu theo yêu cầu người
-- dùng, chưa verify được bằng Encore CLI/Postgres thật trong môi trường này.
CREATE SCHEMA IF NOT EXISTS control_plane;

CREATE TABLE IF NOT EXISTS control_plane.missions (
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

CREATE INDEX IF NOT EXISTS idx_control_plane_missions_tenant_status ON control_plane.missions(tenant_id, status);

CREATE TABLE IF NOT EXISTS control_plane.tasks (
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

CREATE INDEX IF NOT EXISTS idx_control_plane_tasks_mission ON control_plane.tasks(mission_id);
CREATE INDEX IF NOT EXISTS idx_control_plane_tasks_status ON control_plane.tasks(status);

CREATE TABLE IF NOT EXISTS control_plane.assignments (
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
CREATE UNIQUE INDEX IF NOT EXISTS idx_control_plane_assignments_task_active_lease
    ON control_plane.assignments(task_id) WHERE status = 'leased';
CREATE INDEX IF NOT EXISTS idx_control_plane_assignments_worker ON control_plane.assignments(worker_id);

-- ============================================================================
-- from services/cosa/migrations/8_control_plane_watches_signals.up.sql
-- ============================================================================
-- Wave 7 — Watch/Signal/Trigger cho proactive agent (Blueprint V2 §71.1).
CREATE TABLE IF NOT EXISTS control_plane.watches (
    id BIGINT PRIMARY KEY,
    tenant_id BIGINT NOT NULL,
    kind TEXT NOT NULL,
    config JSONB NOT NULL DEFAULT '{}'::jsonb,
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'paused', 'retired')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_control_plane_watches_tenant ON control_plane.watches(tenant_id, status);

CREATE TABLE IF NOT EXISTS control_plane.trigger_policies (
    id BIGINT PRIMARY KEY,
    watch_id BIGINT NOT NULL REFERENCES control_plane.watches(id) ON DELETE CASCADE,
    condition JSONB NOT NULL DEFAULT '{}'::jsonb,
    target_agent_spec_id TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_control_plane_trigger_policies_watch ON control_plane.trigger_policies(watch_id);

-- `dedupe_key` chống duplicate proactive Run cho cùng 1 signal thật (Blueprint
-- V2 Scenario G: "Duplicate signal không tạo duplicate proactive Run/delivery").
CREATE TABLE IF NOT EXISTS control_plane.signal_observations (
    id BIGINT PRIMARY KEY,
    watch_id BIGINT NOT NULL REFERENCES control_plane.watches(id) ON DELETE CASCADE,
    dedupe_key TEXT NOT NULL,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    triggered_run_id TEXT,
    observed_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_control_plane_signal_observations_dedupe
    ON control_plane.signal_observations(watch_id, dedupe_key);

-- ============================================================================
-- from services/cosa/migrations/9_control_plane_delivery.up.sql
-- ============================================================================
-- Wave 7 — Delivery policy + cost ledger (Blueprint V2 §71.1, §28).
CREATE TABLE IF NOT EXISTS control_plane.delivery_policies (
    id BIGINT PRIMARY KEY,
    tenant_id BIGINT NOT NULL,
    channel TEXT NOT NULL CHECK (channel IN ('flutter', 'email', 'slack', 'webhook')),
    config JSONB NOT NULL DEFAULT '{}'::jsonb,
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'paused')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_control_plane_delivery_policies_tenant ON control_plane.delivery_policies(tenant_id);

CREATE TABLE IF NOT EXISTS control_plane.delivery_attempts (
    id BIGINT PRIMARY KEY,
    delivery_policy_id BIGINT NOT NULL REFERENCES control_plane.delivery_policies(id) ON DELETE CASCADE,
    artifact_ref TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'sent', 'failed')),
    error_message TEXT,
    attempted_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_control_plane_delivery_attempts_policy ON control_plane.delivery_attempts(delivery_policy_id);

CREATE TABLE IF NOT EXISTS control_plane.cost_ledger (
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

CREATE INDEX IF NOT EXISTS idx_control_plane_cost_ledger_tenant ON control_plane.cost_ledger(tenant_id, recorded_at);
CREATE INDEX IF NOT EXISTS idx_control_plane_cost_ledger_mission ON control_plane.cost_ledger(mission_id);

-- ============================================================================
-- from services/cosa/migrations/003_cosa_automation_mvp.up.sql
-- ============================================================================
-- COSA Automation MVP (Task 1) — Control Plane dispatch fencing for automation
-- runs. Opaque references ONLY: invocation id, task id, claim token, version/hash,
-- trigger identity. No business content, prompt, credential or connector grant.
-- docs/superpowers/plans/2026-09-10-cosa-automation-mvp.md
--
-- Expand-only. Schema `control_plane` already exists (001 baseline + 002 restore).

CREATE TABLE IF NOT EXISTS control_plane.automation_dispatches (
  invocation_id  TEXT PRIMARY KEY,
  workspace_id   TEXT NOT NULL,
  automation_key TEXT NOT NULL,
  revision       INTEGER NOT NULL,
  revision_hash  TEXT NOT NULL,
  trigger_kind   TEXT NOT NULL,
  trigger_identity TEXT NOT NULL,
  correlation_id TEXT NOT NULL,
  task_id        TEXT,
  claim_token    TEXT,
  state          TEXT NOT NULL DEFAULT 'received'
                   CHECK (state IN ('received', 'scheduled', 'claimed', 'completed', 'failed', 'quarantined')),
  last_error     TEXT,
  created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
  scheduled_at   TIMESTAMPTZ,
  completed_at   TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_automation_dispatches_state
  ON control_plane.automation_dispatches (state, created_at);
CREATE INDEX IF NOT EXISTS idx_automation_dispatches_task
  ON control_plane.automation_dispatches (task_id) WHERE task_id IS NOT NULL;

