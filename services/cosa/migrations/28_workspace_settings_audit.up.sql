-- Migration 28: Workspace Settings Audit Events
CREATE TABLE IF NOT EXISTS control_plane.workspace_settings_audit_events (
    event_id BIGSERIAL PRIMARY KEY,
    workspace_id BIGINT NOT NULL,
    actor_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    target_kind TEXT NOT NULL,
    target_id TEXT NOT NULL,
    details JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_workspace_settings_audit_events_ws ON control_plane.workspace_settings_audit_events (workspace_id, created_at DESC);
