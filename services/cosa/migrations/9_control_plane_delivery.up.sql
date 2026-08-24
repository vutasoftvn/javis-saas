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
