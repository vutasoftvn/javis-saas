-- Migration 029: Local ingestion pipeline state machine (Task 5, plan
-- local-first-enterprise-knowledge) — thay thế state machine trước đây sống
-- trong services/cosa (bảng document_ingestions, TypeScript). Toàn bộ vòng
-- đời ingestion (QUEUED → VALIDATING → CONVERTING → REVIEW_PENDING →
-- PUBLISHED/REJECTED/FAILED) giờ local, khớp ADR-LOCAL-FIRST-001 (execution
-- state cư trú trên Workspace Runtime Node, không phải VPS Platform Control
-- Plane hay 1 service TS trung gian).

CREATE TABLE IF NOT EXISTS agent.local_ingestion_attempts (
    workspace_id TEXT NOT NULL,
    upload_id TEXT NOT NULL,
    state TEXT NOT NULL CHECK (
        state IN (
            'QUEUED', 'VALIDATING', 'CONVERTING', 'REVIEW_PENDING',
            'PUBLISHED', 'REJECTED', 'FAILED'
        )
    ),
    claim_token_hash TEXT,
    quarantine_relative_path TEXT NOT NULL,
    declared_media_type TEXT,
    detected_media_type TEXT,
    source_sha256 TEXT,
    size_bytes BIGINT,
    knowledge_source_id TEXT,
    vault_document_id UUID,
    vault_version_id UUID,
    manifest_json JSONB,
    failure_code TEXT,
    created_by TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (workspace_id, upload_id)
);

CREATE INDEX IF NOT EXISTS idx_local_ingestion_attempts_workspace_state
    ON agent.local_ingestion_attempts (workspace_id, state);

-- Audit trail sanitize (cùng nguyên tắc documentIngestionAuditEvents cũ bên
-- services/cosa) — KHÔNG BAO GIỜ ghi content/markdown/quarantine path/object
-- key thô, chỉ old_state/new_state/reason (mã lỗi allowlist, không traceback).
CREATE TABLE IF NOT EXISTS agent.local_ingestion_events (
    event_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id TEXT NOT NULL,
    upload_id TEXT NOT NULL,
    old_state TEXT,
    new_state TEXT NOT NULL,
    reason TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    FOREIGN KEY (workspace_id, upload_id)
        REFERENCES agent.local_ingestion_attempts(workspace_id, upload_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_local_ingestion_events_workspace_upload
    ON agent.local_ingestion_events (workspace_id, upload_id, created_at DESC);

ALTER TABLE agent.local_ingestion_attempts ENABLE ROW LEVEL SECURITY;
ALTER TABLE agent.local_ingestion_attempts FORCE ROW LEVEL SECURITY;
ALTER TABLE agent.local_ingestion_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE agent.local_ingestion_events FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS local_ingestion_attempts_workspace_isolation ON agent.local_ingestion_attempts;
CREATE POLICY local_ingestion_attempts_workspace_isolation ON agent.local_ingestion_attempts
    FOR ALL
    USING (workspace_id = current_setting('cosa.workspace_id', true))
    WITH CHECK (workspace_id = current_setting('cosa.workspace_id', true));

DROP POLICY IF EXISTS local_ingestion_events_workspace_isolation ON agent.local_ingestion_events;
CREATE POLICY local_ingestion_events_workspace_isolation ON agent.local_ingestion_events
    FOR ALL
    USING (workspace_id = current_setting('cosa.workspace_id', true))
    WITH CHECK (workspace_id = current_setting('cosa.workspace_id', true));
