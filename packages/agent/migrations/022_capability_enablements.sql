-- 022_capability_enablements.sql
-- Create agent_capability_enablements table for durable capability enablement registry

CREATE TABLE IF NOT EXISTS agent_capability_enablements (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    capability_id TEXT NOT NULL,
    skill_id TEXT NOT NULL,
    skill_hash TEXT NOT NULL,
    action_class VARCHAR(20) NOT NULL,
    target_fingerprint TEXT NOT NULL DEFAULT '*',
    permitted_limits JSONB NOT NULL DEFAULT '{}'::jsonb,
    status VARCHAR(30) NOT NULL DEFAULT 'ENABLED',
    source_approval_id TEXT,
    evaluation_ref TEXT,
    rollback_ref TEXT,
    expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_enablement_status
        CHECK (status IN ('ENABLED', 'REVOKED', 'EXPIRED')),
    CONSTRAINT chk_enablement_action_class
        CHECK (action_class IN ('R', 'A', 'B', 'X', 'M', 'D'))
);

CREATE INDEX IF NOT EXISTS idx_cap_enablements_lookup 
    ON agent_capability_enablements(workspace_id, capability_id, skill_hash, action_class, status);
