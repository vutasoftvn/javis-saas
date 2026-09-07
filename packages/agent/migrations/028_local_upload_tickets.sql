-- Migration 028: Local upload ticket durability (Task 3, plan
-- local-first-enterprise-knowledge). Ticket phải sống sót qua restart API/
-- worker process thật (Task 13) — chỉ SHA-256 hash của secret được lưu, KHÔNG
-- BAO GIỜ raw secret hay local path tuyệt đối.

CREATE TABLE IF NOT EXISTS agent.local_upload_tickets (
    workspace_id TEXT NOT NULL,
    upload_id TEXT NOT NULL,
    secret_hash TEXT NOT NULL,
    max_bytes BIGINT NOT NULL CHECK (max_bytes > 0),
    expires_at TIMESTAMPTZ NOT NULL,
    quarantine_relative_path TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (workspace_id, upload_id)
);

CREATE INDEX IF NOT EXISTS idx_local_upload_tickets_expires_at
    ON agent.local_upload_tickets (expires_at);

ALTER TABLE agent.local_upload_tickets ENABLE ROW LEVEL SECURITY;
ALTER TABLE agent.local_upload_tickets FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS local_upload_tickets_workspace_isolation ON agent.local_upload_tickets;
CREATE POLICY local_upload_tickets_workspace_isolation ON agent.local_upload_tickets
    FOR ALL
    USING (workspace_id = current_setting('cosa.workspace_id', true))
    WITH CHECK (workspace_id = current_setting('cosa.workspace_id', true));
