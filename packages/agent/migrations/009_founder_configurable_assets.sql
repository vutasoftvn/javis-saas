-- Migration 009: Founder-Configurable Assets Storage (Agent Platform)
--
-- Adds durable storage for:
-- 1. Custom Agent, Skill and Workflow metadata and scope
-- 2. Immutable asset versions with canonical hash
-- 3. Asset evaluations for structural and policy guarantees
-- 4. Audit events for lifecycle state transitions

CREATE TABLE IF NOT EXISTS agent.workspace_assets (
    workspace_id varchar(64) NOT NULL,
    asset_id varchar(256) NOT NULL,
    kind varchar(32) NOT NULL,
    name varchar(256) NOT NULL,
    description text,
    scope_kind varchar(32) NOT NULL,
    project_id varchar(64),
    origin_kind varchar(32) NOT NULL,
    origin_asset_id varchar(256),
    origin_version varchar(64),
    origin_definition_hash varchar(128),
    current_draft_version varchar(64),
    published_version varchar(64),
    created_by varchar(128) NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (workspace_id, asset_id),
    CONSTRAINT check_sandbox_project CHECK (
        (scope_kind = 'PROJECT_SANDBOX' AND project_id IS NOT NULL) OR
        (scope_kind = 'WORKSPACE' AND project_id IS NULL)
    ),
    CONSTRAINT check_asset_kind CHECK (
        kind IN ('AGENT', 'SKILL', 'WORKFLOW')
    )
);

CREATE TABLE IF NOT EXISTS agent.workspace_asset_versions (
    workspace_id varchar(64) NOT NULL,
    asset_id varchar(256) NOT NULL,
    version varchar(64) NOT NULL,
    definition_hash varchar(128) NOT NULL,
    content_json jsonb NOT NULL,
    lifecycle varchar(32) NOT NULL DEFAULT 'DRAFT',
    scope_kind varchar(32) NOT NULL,
    project_id varchar(64),
    origin_json jsonb,
    evaluation_summary jsonb,
    created_by varchar(128) NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    published_at timestamptz,
    PRIMARY KEY (workspace_id, asset_id, version),
    UNIQUE (workspace_id, asset_id, definition_hash),
    FOREIGN KEY (workspace_id, asset_id) REFERENCES agent.workspace_assets(workspace_id, asset_id) ON DELETE CASCADE,
    CONSTRAINT check_version_sandbox_project CHECK (
        (scope_kind = 'PROJECT_SANDBOX' AND project_id IS NOT NULL) OR
        (scope_kind = 'WORKSPACE' AND project_id IS NULL)
    ),
    CONSTRAINT check_lifecycle CHECK (
        lifecycle IN ('DRAFT', 'CANDIDATE', 'EVALUATING', 'REVIEW_REQUIRED', 'PUBLISHED', 'RETIRED')
    )
);

CREATE TABLE IF NOT EXISTS agent.asset_evaluations (
    evaluation_id varchar(64) PRIMARY KEY,
    workspace_id varchar(64) NOT NULL,
    asset_id varchar(256) NOT NULL,
    version varchar(64) NOT NULL,
    definition_hash varchar(128) NOT NULL,
    status varchar(32) NOT NULL,
    structural_result jsonb NOT NULL DEFAULT '{}'::jsonb,
    negative_policy_result jsonb NOT NULL DEFAULT '{}'::jsonb,
    scenario_suite_result jsonb NOT NULL DEFAULT '{}'::jsonb,
    evidence_refs jsonb NOT NULL DEFAULT '[]'::jsonb,
    cost_latency_summary jsonb NOT NULL DEFAULT '{}'::jsonb,
    evaluator_version varchar(64) NOT NULL,
    evaluated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS agent.asset_events (
    event_id varchar(64) PRIMARY KEY,
    workspace_id varchar(64) NOT NULL,
    asset_id varchar(256) NOT NULL,
    version varchar(64),
    event_type varchar(64) NOT NULL,
    from_lifecycle varchar(32),
    to_lifecycle varchar(32),
    actor_id varchar(128) NOT NULL,
    payload jsonb NOT NULL DEFAULT '{}'::jsonb,
    occurred_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_workspace_assets_ws ON agent.workspace_assets(workspace_id);
CREATE INDEX IF NOT EXISTS idx_workspace_assets_proj ON agent.workspace_assets(workspace_id, project_id);
CREATE INDEX IF NOT EXISTS idx_workspace_asset_versions_ws_asset ON agent.workspace_asset_versions(workspace_id, asset_id);
CREATE INDEX IF NOT EXISTS idx_asset_evaluations_asset_ver ON agent.asset_evaluations(workspace_id, asset_id, version);
CREATE INDEX IF NOT EXISTS idx_asset_events_asset_time ON agent.asset_events(workspace_id, asset_id, occurred_at DESC);
