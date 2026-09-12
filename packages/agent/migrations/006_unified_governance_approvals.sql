-- Migration 006: Unified Governance Approvals
--
-- Expands canonical agent.approvals ledger to support both TOOL_CALL
-- and CHANGE_REQUEST bindings.
-- Adds agent.approval_events (audit trail) and agent.approval_action_outbox (reliable action dispatch).

ALTER TABLE agent.approvals
    ADD COLUMN IF NOT EXISTS workspace_id varchar(64),
    ADD COLUMN IF NOT EXISTS binding_kind varchar(32) NOT NULL DEFAULT 'TOOL_CALL',
    ADD COLUMN IF NOT EXISTS subject_kind varchar(128),
    ADD COLUMN IF NOT EXISTS subject_ref varchar(256),
    ADD COLUMN IF NOT EXISTS subject_hash varchar(128);

UPDATE agent.approvals AS a
SET workspace_id = r.workspace_id
FROM agent.runs AS r
WHERE a.run_id = r.run_id AND a.workspace_id IS NULL;

ALTER TABLE agent.approvals
    ALTER COLUMN run_id DROP NOT NULL,
    ALTER COLUMN tool_call_id DROP NOT NULL,
    ALTER COLUMN checkpoint_ref DROP NOT NULL;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'chk_agent_approvals_binding'
          AND conrelid = 'agent.approvals'::regclass
    ) THEN
        ALTER TABLE agent.approvals ADD CONSTRAINT chk_agent_approvals_binding
        CHECK (
          (binding_kind = 'TOOL_CALL'
           AND run_id IS NOT NULL AND tool_call_id IS NOT NULL AND checkpoint_ref IS NOT NULL)
          OR
          (binding_kind = 'CHANGE_REQUEST' AND workspace_id IS NOT NULL
           AND run_id IS NULL AND tool_call_id IS NULL AND checkpoint_ref IS NULL
           AND subject_kind IS NOT NULL AND subject_ref IS NOT NULL AND subject_hash IS NOT NULL)
        ) NOT VALID;
        ALTER TABLE agent.approvals VALIDATE CONSTRAINT chk_agent_approvals_binding;
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_agent_approvals_workspace
ON agent.approvals (workspace_id);

CREATE UNIQUE INDEX IF NOT EXISTS ux_agent_approvals_pending_change_subject
ON agent.approvals (workspace_id, action, subject_kind, subject_ref, subject_hash)
WHERE binding_kind = 'CHANGE_REQUEST' AND status = 'pending';

-- Audit trail for all approval decisions and state changes
CREATE TABLE IF NOT EXISTS agent.approval_events (
    event_id varchar(64) PRIMARY KEY,
    approval_id varchar(64) NOT NULL REFERENCES agent.approvals(approval_id) ON DELETE CASCADE,
    workspace_id varchar(64) NOT NULL,
    event_type varchar(64) NOT NULL,
    actor_id varchar(128),
    payload jsonb DEFAULT '{}'::jsonb NOT NULL,
    created_at timestamptz DEFAULT now() NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_agent_approval_events_workspace_created
ON agent.approval_events (workspace_id, created_at);

-- Action outbox for executing approved changes durably and idempotently
CREATE TABLE IF NOT EXISTS agent.approval_action_outbox (
    outbox_id varchar(64) PRIMARY KEY,
    approval_id varchar(64) NOT NULL UNIQUE REFERENCES agent.approvals(approval_id) ON DELETE CASCADE,
    workspace_id varchar(64) NOT NULL,
    action varchar(128) NOT NULL,
    subject_kind varchar(128),
    subject_ref varchar(256),
    subject_hash varchar(128) NOT NULL,
    state varchar(32) DEFAULT 'pending' NOT NULL,
    attempt_count integer DEFAULT 0 NOT NULL,
    next_attempt_at timestamptz DEFAULT now() NOT NULL,
    claim_token varchar(128),
    created_at timestamptz DEFAULT now() NOT NULL,
    delivered_at timestamptz
);

CREATE INDEX IF NOT EXISTS idx_agent_approval_action_outbox_state_next
ON agent.approval_action_outbox (state, next_attempt_at);
