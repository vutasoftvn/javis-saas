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
