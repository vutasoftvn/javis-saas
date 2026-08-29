-- Migration: 001_canonical_agent_schema.sql
-- Description: Khởi tạo 5 bảng canonical của Durable Run Substrate theo Master Guide §11 & Implementation Plan Phase 2.

CREATE SCHEMA IF NOT EXISTS agent;

-- 1. agent.runs: Sở hữu vòng đời logic của Run
CREATE TABLE IF NOT EXISTS agent.runs (
    run_id VARCHAR(64) PRIMARY KEY,
    tenant_id VARCHAR(64),
    company_id VARCHAR(64),
    workspace_id VARCHAR(64),
    conversation_id VARCHAR(64),
    session_ref VARCHAR(128),
    principal VARCHAR(128) NOT NULL,
    root_executable_id VARCHAR(128) NOT NULL,
    root_executable_kind VARCHAR(32) NOT NULL DEFAULT 'agent',
    root_executable_version VARCHAR(32) NOT NULL DEFAULT '1.0.0',
    root_definition_hash VARCHAR(64),
    status VARCHAR(32) NOT NULL DEFAULT 'pending',
    execution_mode VARCHAR(32) NOT NULL DEFAULT 'autonomous',
    correlation_id VARCHAR(128),
    idempotency_key VARCHAR(128),
    input_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    model_policy JSONB NOT NULL DEFAULT '{}'::jsonb,
    final_output JSONB,
    usage JSONB NOT NULL DEFAULT '{}'::jsonb,
    error_details JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_agent_runs_workspace_status ON agent.runs(workspace_id, status);
CREATE INDEX IF NOT EXISTS idx_agent_runs_tenant ON agent.runs(tenant_id);
CREATE INDEX IF NOT EXISTS idx_agent_runs_correlation ON agent.runs(correlation_id);
CREATE INDEX IF NOT EXISTS idx_agent_runs_idempotency ON agent.runs(idempotency_key);

-- 2. agent.run_checkpoints: Điểm kiểm soát tuần tự để resume an toàn
CREATE TABLE IF NOT EXISTS agent.run_checkpoints (
    checkpoint_ref VARCHAR(128) PRIMARY KEY,
    run_id VARCHAR(64) NOT NULL REFERENCES agent.runs(run_id) ON DELETE CASCADE,
    sequence_no INT NOT NULL,
    step_name VARCHAR(128),
    state_kind VARCHAR(32) NOT NULL DEFAULT 'workflow',
    serialized_state JSONB NOT NULL DEFAULT '{}'::jsonb,
    manifest_snapshot JSONB NOT NULL DEFAULT '{}'::jsonb,
    resume_metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_agent_checkpoint_run_seq UNIQUE (run_id, sequence_no)
);

CREATE INDEX IF NOT EXISTS idx_agent_checkpoints_run ON agent.run_checkpoints(run_id);

-- 3. agent.run_events: Append-only operational event ledger
CREATE TABLE IF NOT EXISTS agent.run_events (
    event_id VARCHAR(64) PRIMARY KEY,
    run_id VARCHAR(64) NOT NULL REFERENCES agent.runs(run_id) ON DELETE CASCADE,
    sequence_no BIGSERIAL,
    event_type VARCHAR(64) NOT NULL,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    correlation_id VARCHAR(128),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_agent_events_run_seq ON agent.run_events(run_id, sequence_no);
CREATE INDEX IF NOT EXISTS idx_agent_events_type ON agent.run_events(event_type);

-- 4. agent.run_tool_calls: Exact invocation ledger
CREATE TABLE IF NOT EXISTS agent.run_tool_calls (
    tool_call_id VARCHAR(128) PRIMARY KEY,
    run_id VARCHAR(64) NOT NULL REFERENCES agent.runs(run_id) ON DELETE CASCADE,
    checkpoint_ref VARCHAR(128),
    capability_id VARCHAR(128) NOT NULL,
    payload_hash VARCHAR(64) NOT NULL,
    input_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    status VARCHAR(32) NOT NULL DEFAULT 'pending',
    idempotency_key VARCHAR(128),
    result_hash VARCHAR(64),
    output_payload JSONB,
    error_message TEXT,
    execution_target_snapshot JSONB NOT NULL DEFAULT '{}'::jsonb,
    governance_state JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_agent_tool_calls_run ON agent.run_tool_calls(run_id);
CREATE INDEX IF NOT EXISTS idx_agent_tool_calls_cap ON agent.run_tool_calls(capability_id);
CREATE INDEX IF NOT EXISTS idx_agent_tool_calls_idempotency ON agent.run_tool_calls(run_id, idempotency_key);

-- 5. agent.approvals: Phê duyệt con người ràng buộc với checkpoint và tool_call
CREATE TABLE IF NOT EXISTS agent.approvals (
    approval_id VARCHAR(64) PRIMARY KEY,
    run_id VARCHAR(64) NOT NULL REFERENCES agent.runs(run_id) ON DELETE CASCADE,
    tool_call_id VARCHAR(128) NOT NULL REFERENCES agent.run_tool_calls(tool_call_id) ON DELETE CASCADE,
    checkpoint_ref VARCHAR(128) NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'pending',
    requirement JSONB NOT NULL DEFAULT '{}'::jsonb,
    requester VARCHAR(128),
    action VARCHAR(128),
    subject TEXT,
    reviewer VARCHAR(128),
    reason TEXT,
    evidence JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    decided_at TIMESTAMPTZ,
    expires_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_agent_approvals_run ON agent.approvals(run_id);
CREATE INDEX IF NOT EXISTS idx_agent_approvals_tool_call ON agent.approvals(tool_call_id);
CREATE INDEX IF NOT EXISTS idx_agent_approvals_checkpoint ON agent.approvals(checkpoint_ref);
CREATE INDEX IF NOT EXISTS idx_agent_approvals_status ON agent.approvals(status);
