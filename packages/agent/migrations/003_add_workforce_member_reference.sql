-- Migration 003: Add workforce member reference to workforce_assignments
-- Bind agent assignments to Company AI workforce identity (Founder-Controlled Workforce Authorization)

CREATE TABLE IF NOT EXISTS agent.workforce_employees (
    agent_instance_id UUID PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    employee_code TEXT NOT NULL,
    display_name TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('ACTIVE', 'SUSPENDED', 'RETIRED')),
    created_by TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    suspended_at TIMESTAMPTZ,
    retired_at TIMESTAMPTZ,
    UNIQUE (workspace_id, employee_code)
);

CREATE TABLE IF NOT EXISTS agent.workforce_assignments (
    assignment_id UUID PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    functional_key TEXT NOT NULL,
    spec_id TEXT NOT NULL,
    spec_version TEXT NOT NULL,
    definition_hash TEXT NOT NULL,
    reports_to_assignment_id UUID,
    configured_by TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    retired_at TIMESTAMPTZ,
    agent_instance_id UUID,
    company_workforce_member_id TEXT,
    UNIQUE (workspace_id, functional_key, spec_id, spec_version, definition_hash)
);

ALTER TABLE agent.workforce_assignments ADD COLUMN IF NOT EXISTS company_workforce_member_id TEXT;
