-- Down migration 004: Project-scoped Founder Hub
--
-- Refuses to run if any Project-scoped data has been written since 004
-- applied — dropping these columns would silently delete Project audit
-- context. Only safe when every touched row is still LEGACY_UNSCOPED /
-- project_id IS NULL (i.e. no application code ever wrote scoped data).

DO $$
DECLARE
    scoped_conversations bigint;
    scoped_messages bigint;
    scoped_runs bigint;
    scoped_checkpoints bigint;
    scoped_tool_calls bigint;
    scoped_approvals bigint;
    scoped_run_events bigint;
    scoped_stream_events bigint;
BEGIN
    SELECT count(*) INTO scoped_conversations
        FROM agent_conversation.conversations WHERE scope_state = 'PROJECT_SCOPED';
    SELECT count(*) INTO scoped_messages
        FROM agent_conversation.messages WHERE project_id IS NOT NULL;
    SELECT count(*) INTO scoped_runs
        FROM agent.runs WHERE project_id IS NOT NULL;
    SELECT count(*) INTO scoped_checkpoints
        FROM agent.run_checkpoints WHERE project_id IS NOT NULL;
    SELECT count(*) INTO scoped_tool_calls
        FROM agent.run_tool_calls WHERE project_id IS NOT NULL;
    SELECT count(*) INTO scoped_approvals
        FROM agent.approvals WHERE project_id IS NOT NULL;
    SELECT count(*) INTO scoped_run_events
        FROM agent.run_events WHERE project_id IS NOT NULL;
    SELECT count(*) INTO scoped_stream_events
        FROM agent_conversation.run_stream_events WHERE project_id IS NOT NULL;

    IF scoped_conversations > 0 OR scoped_messages > 0 OR scoped_runs > 0
        OR scoped_checkpoints > 0 OR scoped_tool_calls > 0 OR scoped_approvals > 0
        OR scoped_run_events > 0 OR scoped_stream_events > 0
    THEN
        RAISE EXCEPTION
            'migration 004 down refused: PROJECT_SCOPED/project_id data present '
            '(conversations=%, messages=%, runs=%, checkpoints=%, tool_calls=%, '
            'approvals=%, run_events=%, stream_events=%) — rolling back would '
            'silently delete Project audit context',
            scoped_conversations, scoped_messages, scoped_runs, scoped_checkpoints,
            scoped_tool_calls, scoped_approvals, scoped_run_events, scoped_stream_events;
    END IF;
END $$;

DROP INDEX IF EXISTS agent_conversation.idx_run_stream_events_project;
ALTER TABLE agent_conversation.run_stream_events
    DROP COLUMN IF EXISTS project_id,
    DROP COLUMN IF EXISTS workspace_id;

ALTER TABLE agent.run_events
    DROP COLUMN IF EXISTS project_id;

ALTER TABLE agent.approvals
    DROP COLUMN IF EXISTS project_id;

ALTER TABLE agent.run_tool_calls
    DROP COLUMN IF EXISTS project_id;

ALTER TABLE agent.run_checkpoints
    DROP COLUMN IF EXISTS project_id;

DROP INDEX IF EXISTS agent.idx_agent_runs_project;
ALTER TABLE agent.runs
    DROP COLUMN IF EXISTS project_id;

ALTER TABLE agent_conversation.messages
    DROP COLUMN IF EXISTS project_id;

DROP INDEX IF EXISTS agent_conversation.idx_agent_conversation_conversations_project;
ALTER TABLE agent_conversation.conversations
    DROP CONSTRAINT IF EXISTS chk_agent_conversation_conversations_project_scope,
    DROP CONSTRAINT IF EXISTS chk_agent_conversation_conversations_scope_state,
    DROP COLUMN IF EXISTS scope_state,
    DROP COLUMN IF EXISTS project_id;
