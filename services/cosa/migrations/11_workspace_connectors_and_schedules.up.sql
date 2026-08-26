-- Migration 11: Workspace Connectors & Schedules
-- Connectors (installations, authorizations, session grants) and business schedules (definitions, executions)

CREATE TABLE IF NOT EXISTS control_plane.workspace_connector_installations (
    id TEXT PRIMARY KEY,
    company_id TEXT NOT NULL,
    workspace_id TEXT NOT NULL,
    connector_key TEXT NOT NULL,
    installed_by TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'enabled',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_connector_installation UNIQUE (company_id, workspace_id, connector_key),
    CONSTRAINT chk_installation_status CHECK (status IN ('enabled', 'disabled'))
);

CREATE TABLE IF NOT EXISTS control_plane.connector_authorizations (
    id TEXT PRIMARY KEY,
    installation_id TEXT NOT NULL REFERENCES control_plane.workspace_connector_installations(id) ON DELETE CASCADE,
    principal_id TEXT NOT NULL,
    secret_ref TEXT NOT NULL,
    granted_scopes JSONB NOT NULL DEFAULT '[]'::jsonb,
    state TEXT NOT NULL DEFAULT 'active',
    expires_at TIMESTAMPTZ NOT NULL,
    revoked_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_authorization_state CHECK (state IN ('active', 'expired', 'revoked'))
);

CREATE TABLE IF NOT EXISTS control_plane.session_connector_grants (
    id TEXT PRIMARY KEY,
    company_id TEXT NOT NULL,
    workspace_id TEXT NOT NULL,
    conversation_id TEXT NOT NULL,
    authorization_id TEXT NOT NULL REFERENCES control_plane.connector_authorizations(id) ON DELETE CASCADE,
    granted_by TEXT NOT NULL,
    allowed_actions JSONB NOT NULL DEFAULT '[]'::jsonb,
    state TEXT NOT NULL DEFAULT 'enabled',
    expires_at TIMESTAMPTZ,
    revoked_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_session_grant UNIQUE (conversation_id, authorization_id),
    CONSTRAINT chk_session_grant_state CHECK (state IN ('enabled', 'revoked', 'expired'))
);

CREATE TABLE IF NOT EXISTS control_plane.workspace_schedule_definitions (
    id TEXT PRIMARY KEY,
    company_id TEXT NOT NULL,
    workspace_id TEXT NOT NULL,
    created_by TEXT NOT NULL,
    schedule_kind TEXT NOT NULL,
    timezone TEXT NOT NULL DEFAULT 'Asia/Ho_Chi_Minh',
    run_at TIMESTAMPTZ,
    hour INT,
    minute INT,
    weekdays JSONB NOT NULL DEFAULT '[]'::jsonb,
    prompt_template TEXT NOT NULL,
    agent_profile TEXT NOT NULL DEFAULT 'operations',
    connector_grant_ids JSONB NOT NULL DEFAULT '[]'::jsonb,
    state TEXT NOT NULL DEFAULT 'enabled',
    next_run_at TIMESTAMPTZ,
    last_run_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_schedule_kind CHECK (schedule_kind IN ('one_time', 'daily', 'weekdays')),
    CONSTRAINT chk_schedule_state CHECK (state IN ('enabled', 'paused', 'archived'))
);

CREATE INDEX IF NOT EXISTS idx_workspace_schedules_due
    ON control_plane.workspace_schedule_definitions(state, next_run_at);

CREATE TABLE IF NOT EXISTS control_plane.workspace_schedule_executions (
    id TEXT PRIMARY KEY,
    definition_id TEXT NOT NULL REFERENCES control_plane.workspace_schedule_definitions(id) ON DELETE CASCADE,
    company_id TEXT NOT NULL,
    workspace_id TEXT NOT NULL,
    scheduled_for TIMESTAMPTZ NOT NULL,
    prompt_template_snapshot TEXT NOT NULL,
    agent_profile_snapshot TEXT NOT NULL,
    connector_grant_ids_snapshot JSONB NOT NULL DEFAULT '[]'::jsonb,
    state TEXT NOT NULL DEFAULT 'queued',
    task_id TEXT,
    conversation_id TEXT,
    run_id TEXT,
    error TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_schedule_execution UNIQUE (definition_id, scheduled_for),
    CONSTRAINT chk_schedule_execution_state CHECK (state IN ('queued', 'running', 'succeeded', 'failed', 'blocked_reauth', 'cancelled'))
);

CREATE INDEX IF NOT EXISTS idx_workspace_schedule_executions_lookup
    ON control_plane.workspace_schedule_executions(company_id, workspace_id, scheduled_for DESC);
