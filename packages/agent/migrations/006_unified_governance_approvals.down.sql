-- Down migration 006: Unified Governance Approvals
--
-- Refuses to run if any CHANGE_REQUEST data or approval events/outbox records exist.

DO $$
DECLARE
    change_approvals bigint;
    events_count bigint;
    outbox_count bigint;
BEGIN
    SELECT count(*) INTO change_approvals
        FROM agent.approvals WHERE binding_kind = 'CHANGE_REQUEST';
    SELECT count(*) INTO events_count
        FROM agent.approval_events;
    SELECT count(*) INTO outbox_count
        FROM agent.approval_action_outbox;

    IF change_approvals > 0 OR events_count > 0 OR outbox_count > 0 THEN
        RAISE EXCEPTION
            'migration 006 down refused: CHANGE_REQUEST approvals or approval_events/outbox records present '
            '(change_approvals=%, events=%, outbox=%) — rolling back would silently delete audit or promotion evidence',
            change_approvals, events_count, outbox_count;
    END IF;
END $$;

DROP TABLE IF EXISTS agent.approval_action_outbox;
DROP TABLE IF EXISTS agent.approval_events;

DROP INDEX IF EXISTS agent.ux_agent_approvals_pending_change_subject;
DROP INDEX IF EXISTS agent.idx_agent_approvals_workspace;

ALTER TABLE agent.approvals DROP CONSTRAINT IF EXISTS chk_agent_approvals_binding;

ALTER TABLE agent.approvals
    ALTER COLUMN run_id SET NOT NULL,
    ALTER COLUMN tool_call_id SET NOT NULL,
    ALTER COLUMN checkpoint_ref SET NOT NULL;

ALTER TABLE agent.approvals
    DROP COLUMN IF EXISTS subject_hash,
    DROP COLUMN IF EXISTS subject_ref,
    DROP COLUMN IF EXISTS subject_kind,
    DROP COLUMN IF EXISTS binding_kind,
    DROP COLUMN IF EXISTS workspace_id;
