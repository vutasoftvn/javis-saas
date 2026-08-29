-- Rollback 004_harden_exact_invocation_and_approval.sql
ALTER TABLE agent.approvals
    DROP COLUMN IF EXISTS resolved_at,
    DROP COLUMN IF EXISTS previous_status;

ALTER TABLE agent.approvals
    DROP CONSTRAINT IF EXISTS approvals_tool_call_id_fkey;

ALTER TABLE agent.run_tool_calls
    DROP CONSTRAINT IF EXISTS uq_agent_run_tool_calls_tool_call_id;

ALTER TABLE agent.run_tool_calls
    DROP CONSTRAINT IF EXISTS run_tool_calls_pkey;

ALTER TABLE agent.run_tool_calls
    ADD CONSTRAINT run_tool_calls_pkey PRIMARY KEY (tool_call_id);

ALTER TABLE agent.approvals
    ADD CONSTRAINT approvals_tool_call_id_fkey
    FOREIGN KEY (tool_call_id)
    REFERENCES agent.run_tool_calls(tool_call_id)
    ON DELETE CASCADE;
