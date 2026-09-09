-- Migration 036: Founder delegation cho workforce control (Task 6).
--
-- Delegation explicit + revocable, scope theo action + functional-key hoặc
-- principal, có expiry và grant/revoke event bất biến (spec §5.3). KHÔNG tái
-- dùng approval.requirement.role. Expand-only + có down.

CREATE TABLE IF NOT EXISTS agent.workforce_delegations (
    delegation_id     UUID PRIMARY KEY,
    workspace_id      TEXT NOT NULL,
    grantor_id        TEXT NOT NULL,
    principal_id      TEXT NOT NULL,
    action_scope      TEXT NOT NULL,   -- evaluation | queue_control | review_override
    functional_key    TEXT NULL,       -- NULL = mọi functional key
    status            TEXT NOT NULL DEFAULT 'ACTIVE' CHECK (status IN ('ACTIVE','REVOKED')),
    granted_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at        TIMESTAMPTZ NULL,
    revoked_at        TIMESTAMPTZ NULL,
    revoked_by        TEXT NULL
);

CREATE INDEX IF NOT EXISTS idx_workforce_delegations_lookup
    ON agent.workforce_delegations (workspace_id, principal_id, action_scope, status);

CREATE TABLE IF NOT EXISTS agent.workforce_delegation_events (
    event_id       UUID PRIMARY KEY,
    delegation_id  UUID NOT NULL REFERENCES agent.workforce_delegations(delegation_id) ON DELETE CASCADE,
    workspace_id   TEXT NOT NULL,
    event_type     TEXT NOT NULL,     -- granted | revoked
    actor_id       TEXT NOT NULL,
    payload        JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);
