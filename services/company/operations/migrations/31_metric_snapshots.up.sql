-- 31_metric_snapshots.up.sql
-- Create metric_snapshots table for idempotent validated metric telemetry

CREATE TABLE IF NOT EXISTS strategy.metric_snapshots (
    id BIGINT PRIMARY KEY,
    workspace_id BIGINT NOT NULL,
    project_id BIGINT NOT NULL REFERENCES strategy.projects(id) ON DELETE CASCADE,
    contract_version_id BIGINT NOT NULL REFERENCES strategy.metric_contracts(id) ON DELETE CASCADE,
    source_system VARCHAR(50) NOT NULL,
    source_window VARCHAR(50) NOT NULL,
    source_record_id TEXT NOT NULL,
    payload_hash TEXT NOT NULL,
    observed_at TIMESTAMPTZ NOT NULL,
    captured_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    value DOUBLE PRECISION NOT NULL,
    numerator DOUBLE PRECISION,
    denominator DOUBLE PRECISION,
    quality_status VARCHAR(30) NOT NULL DEFAULT 'VALID',
    quality_checks JSONB NOT NULL DEFAULT '{}'::jsonb,
    evidence_ingestion_id BIGINT REFERENCES strategy.evidence_ingestions(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT metric_snapshots_quality_chk
        CHECK (quality_status IN ('VALID', 'STALE', 'INCOMPLETE', 'REJECTED')),
    CONSTRAINT uq_metric_snapshot_idempotent
        UNIQUE (workspace_id, contract_version_id, source_system, source_record_id, payload_hash)
);

CREATE INDEX IF NOT EXISTS idx_metric_snapshots_ws_proj ON strategy.metric_snapshots(workspace_id, project_id);
CREATE INDEX IF NOT EXISTS idx_metric_snapshots_contract ON strategy.metric_snapshots(workspace_id, contract_version_id);
CREATE INDEX IF NOT EXISTS idx_metric_snapshots_observed ON strategy.metric_snapshots(workspace_id, observed_at);
