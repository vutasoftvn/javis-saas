-- Migration 011: Workflow Definition, Execution Manifest & Step Record Persistence (Agent Platform)
--
-- Task 8: Persist workflow definitions, bindings and execution manifests durably.
-- Tables created:
-- 1. agent.workflow_definitions: Immutable published/saved workflow specs keyed by (workspace_id, workflow_asset_id, version).
-- 2. agent.workflow_execution_manifests: Pinned execution manifests bound to project_id and run_id. Insert-once per run_id.
-- 3. agent.workflow_step_records: Durable step ledger per run with hashes, checkpoints, and safe reason codes (no raw secrets).

CREATE TABLE IF NOT EXISTS agent.workflow_definitions (
    workspace_id varchar(64) NOT NULL DEFAULT 'default',
    workflow_asset_id varchar(256) NOT NULL,
    version varchar(64) NOT NULL,
    definition_hash varchar(128) NOT NULL,
    spec_data jsonb NOT NULL,
    description text,
    created_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (workspace_id, workflow_asset_id, version),
    UNIQUE (workspace_id, workflow_asset_id, definition_hash)
);

CREATE INDEX IF NOT EXISTS idx_workflow_definitions_hash
    ON agent.workflow_definitions (definition_hash);

CREATE INDEX IF NOT EXISTS idx_workflow_definitions_ws_asset
    ON agent.workflow_definitions (workspace_id, workflow_asset_id);

CREATE TABLE IF NOT EXISTS agent.workflow_execution_manifests (
    run_id varchar(128) PRIMARY KEY,
    manifest_hash varchar(128) NOT NULL,
    project_id varchar(64) NOT NULL,
    workspace_id varchar(64) NOT NULL DEFAULT 'default',
    workflow_asset_id varchar(256) NOT NULL,
    workflow_version varchar(64) NOT NULL,
    workflow_definition_hash varchar(128) NOT NULL,
    role_deployment_id varchar(64),
    project_agent_deployment_id varchar(64),
    pinned_agent_specs jsonb NOT NULL DEFAULT '{}'::jsonb,
    pinned_skill_specs jsonb NOT NULL DEFAULT '{}'::jsonb,
    policy_epoch varchar(64) NOT NULL DEFAULT 'v1',
    policy_hash varchar(128) NOT NULL,
    capability_allowlist jsonb NOT NULL DEFAULT '[]'::jsonb,
    budget_limit jsonb NOT NULL DEFAULT '{}'::jsonb,
    trigger_id varchar(128),
    correlation_id varchar(128),
    evidence_refs jsonb NOT NULL DEFAULT '[]'::jsonb,
    manifest_json jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_workflow_manifests_proj
    ON agent.workflow_execution_manifests (project_id);

CREATE INDEX IF NOT EXISTS idx_workflow_manifests_hash
    ON agent.workflow_execution_manifests (manifest_hash);

CREATE INDEX IF NOT EXISTS idx_workflow_manifests_ws
    ON agent.workflow_execution_manifests (workspace_id);

CREATE TABLE IF NOT EXISTS agent.workflow_step_records (
    step_record_id varchar(128) PRIMARY KEY,
    run_id varchar(128) NOT NULL,
    step_id varchar(128) NOT NULL,
    step_name varchar(256) NOT NULL,
    sequence_no integer NOT NULL,
    status varchar(32) NOT NULL DEFAULT 'PENDING',
    checkpoint_ref varchar(128),
    input_hash varchar(128) NOT NULL,
    output_hash varchar(128),
    safe_reason_code varchar(128),
    error_details jsonb,
    created_at timestamptz NOT NULL DEFAULT now(),
    completed_at timestamptz,
    UNIQUE (run_id, step_id),
    UNIQUE (run_id, sequence_no)
);

CREATE INDEX IF NOT EXISTS idx_workflow_step_records_run
    ON agent.workflow_step_records (run_id);
