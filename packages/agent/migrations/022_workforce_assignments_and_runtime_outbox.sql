-- Migration: 022_workforce_assignments_and_runtime_outbox.sql
-- Description: Workspace workforce assignments, runtime signal outbox, and run cost observations.

CREATE TABLE IF NOT EXISTS agent.workforce_assignments (
    assignment_id UUID PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    functional_key TEXT NOT NULL,
    spec_id TEXT NOT NULL,
    spec_version TEXT NOT NULL,
    definition_hash TEXT NOT NULL,
    reports_to_assignment_id UUID NULL,
    configured_by TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('ACTIVE','RETIRED')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    retired_at TIMESTAMPTZ NULL,
    UNIQUE (workspace_id, functional_key, spec_id, spec_version, definition_hash)
);

CREATE TABLE IF NOT EXISTS agent.runtime_signal_outbox (
    outbox_id UUID PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    source_kind TEXT NOT NULL,
    source_id TEXT NOT NULL,
    sequence BIGINT NOT NULL,
    state TEXT NOT NULL,
    observed_at TIMESTAMPTZ NOT NULL,
    correlation_id TEXT NOT NULL,
    payload_hash TEXT NOT NULL,
    state_delivery TEXT NOT NULL CHECK (state_delivery IN ('PENDING','DELIVERED','FAILED')),
    attempt_count INTEGER NOT NULL DEFAULT 0,
    next_attempt_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    delivered_at TIMESTAMPTZ NULL,
    UNIQUE (workspace_id, source_kind, source_id, sequence)
);

CREATE TABLE IF NOT EXISTS agent.run_cost_observations (
    observation_id UUID PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    run_id TEXT NOT NULL,
    provider_key TEXT NOT NULL,
    model_key TEXT NOT NULL,
    input_tokens BIGINT NULL CHECK (input_tokens >= 0),
    output_tokens BIGINT NULL CHECK (output_tokens >= 0),
    cost_amount NUMERIC NULL CHECK (cost_amount >= 0),
    currency TEXT NULL,
    observed_at TIMESTAMPTZ NOT NULL,
    UNIQUE (workspace_id, run_id, provider_key, model_key, observed_at)
);

CREATE INDEX IF NOT EXISTS idx_workforce_assignments_ws_status ON agent.workforce_assignments (workspace_id, status);
CREATE INDEX IF NOT EXISTS idx_workforce_assignments_reports_to ON agent.workforce_assignments (workspace_id, reports_to_assignment_id);
CREATE INDEX IF NOT EXISTS idx_runtime_signal_outbox_pending ON agent.runtime_signal_outbox (state_delivery, next_attempt_at);
CREATE INDEX IF NOT EXISTS idx_run_cost_observations_ws_time ON agent.run_cost_observations (workspace_id, observed_at DESC);
