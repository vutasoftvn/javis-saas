-- Migration 016: Workspace Artifacts and Lineage
-- Schema and table for runtime deliverables, reports, tables, and assistant outputs

CREATE SCHEMA IF NOT EXISTS agent_artifact;

CREATE TABLE IF NOT EXISTS agent_artifact.workspace_artifacts (
    artifact_id VARCHAR(64) PRIMARY KEY,
    company_id VARCHAR(64) NOT NULL,
    workspace_id VARCHAR(64) NOT NULL,
    conversation_id VARCHAR(64) NOT NULL,
    run_id VARCHAR(64),
    source_message_id VARCHAR(64),
    artifact_kind VARCHAR(32) NOT NULL,
    display_name VARCHAR(255) NOT NULL,
    media_type VARCHAR(128) NOT NULL,
    object_ref VARCHAR(512) NOT NULL,
    checksum VARCHAR(128),
    size_bytes BIGINT NOT NULL DEFAULT 0,
    status VARCHAR(32) NOT NULL DEFAULT 'available',
    input_artifact_ids JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    archived_at TIMESTAMPTZ,
    CONSTRAINT chk_workspace_artifact_kind CHECK (artifact_kind IN ('assistant_output', 'report', 'table', 'file_export')),
    CONSTRAINT chk_workspace_artifact_status CHECK (status IN ('available', 'failed', 'archived'))
);

CREATE INDEX IF NOT EXISTS idx_workspace_artifacts_lookup
    ON agent_artifact.workspace_artifacts(company_id, workspace_id, conversation_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_workspace_artifacts_run
    ON agent_artifact.workspace_artifacts(run_id);
