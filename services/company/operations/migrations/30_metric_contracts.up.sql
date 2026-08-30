-- 30_metric_contracts.up.sql
-- Create metric_contracts table with versioning and explicit decision semantics

CREATE TABLE IF NOT EXISTS strategy.metric_contracts (
    id BIGINT PRIMARY KEY,
    workspace_id BIGINT NOT NULL,
    project_id BIGINT NOT NULL REFERENCES strategy.projects(id) ON DELETE CASCADE,
    metric_key VARCHAR(100) NOT NULL,
    display_name TEXT NOT NULL,
    unit VARCHAR(50) NOT NULL,
    numerator_definition TEXT NOT NULL,
    denominator_definition TEXT NOT NULL,
    cohort_definition TEXT NOT NULL,
    source_mapping JSONB NOT NULL DEFAULT '{}'::jsonb,
    cadence VARCHAR(50) NOT NULL,
    fresh_until TIMESTAMPTZ,
    guardrail TEXT,
    owner_member_id BIGINT,
    decision_use TEXT NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'DRAFT',
    version INTEGER NOT NULL DEFAULT 1,
    approval_ref TEXT,
    change_rationale TEXT,
    created_by_member_id BIGINT,
    published_by_member_id BIGINT,
    published_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ,
    CONSTRAINT uq_metric_contract_version UNIQUE (workspace_id, project_id, metric_key, version)
);

CREATE INDEX IF NOT EXISTS idx_metric_contracts_ws_proj ON strategy.metric_contracts(workspace_id, project_id);
CREATE INDEX IF NOT EXISTS idx_metric_contracts_key ON strategy.metric_contracts(workspace_id, metric_key);
