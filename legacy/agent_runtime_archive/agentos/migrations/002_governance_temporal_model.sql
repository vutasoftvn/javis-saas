-- Migration: 002_governance_temporal_model.sql
-- Description: Durable storage for the governance/identity temporal model —
--   see COSA_AGENT_CORE_GOVERNANCE_TEMPORAL_MODEL_2026-08-23.md.
-- Storage ownership: schema agent_core_governance owned by packages/agent_core/governance/.
--
-- run_id / tool_call_id are plain TEXT here, not foreign keys — this repo has
-- no runs/run_tool_calls table yet (see the plan's Global Constraints).

CREATE SCHEMA IF NOT EXISTS agent_core_governance;

-- SpecResolutionManifest: append-only set of PinnedSpecIdentity a Run has
-- resolved. Never updated in place, never deleted.
CREATE TABLE IF NOT EXISTS agent_core_governance.spec_resolution_manifest_entries (
    run_id TEXT NOT NULL,
    spec_kind TEXT NOT NULL CHECK (spec_kind IN ('agent', 'workflow')),
    spec_id TEXT NOT NULL,
    spec_version TEXT NOT NULL,
    definition_hash TEXT NOT NULL,
    resolved_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (run_id, spec_kind, spec_id, definition_hash)
);

CREATE INDEX IF NOT EXISTS idx_spec_resolution_manifest_run_id
    ON agent_core_governance.spec_resolution_manifest_entries(run_id);

-- InvocationGovernanceState: current accumulated PolicyDecision for one
-- (run_id, tool_call_id) invocation. Upserted on every accumulate() call.
CREATE TABLE IF NOT EXISTS agent_core_governance.invocation_governance_state (
    run_id TEXT NOT NULL,
    tool_call_id TEXT NOT NULL,
    accumulated JSONB NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (run_id, tool_call_id)
);

-- Append-only observation history behind the accumulator above — this is
-- where provenance (ambient vs historical, PHẦN I §2.5 của tài liệu) lives,
-- since invocation_governance_state only ever holds the latest accumulated
-- value.
CREATE TABLE IF NOT EXISTS agent_core_governance.invocation_governance_history (
    id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    tool_call_id TEXT NOT NULL,
    observation JSONB NOT NULL,
    source TEXT NOT NULL CHECK (source IN ('ambient', 'historical')),
    observed_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_invocation_governance_history_invocation
    ON agent_core_governance.invocation_governance_history(run_id, tool_call_id, observed_at);

-- ApprovalEvidence: separate from the accumulated requirement it may
-- satisfy — evidence can expire (valid_until), the accumulated constraint
-- does not (PHẦN I §2.1/§5 của tài liệu). decided_at/valid_until are TEXT
-- (ISO 8601), matching the Pydantic contract exactly.
CREATE TABLE IF NOT EXISTS agent_core_governance.approval_evidence (
    id TEXT PRIMARY KEY,
    approver TEXT NOT NULL,
    scope TEXT NOT NULL,
    decided_at TEXT NOT NULL,
    valid_until TEXT
);

CREATE INDEX IF NOT EXISTS idx_approval_evidence_scope
    ON agent_core_governance.approval_evidence(scope);
