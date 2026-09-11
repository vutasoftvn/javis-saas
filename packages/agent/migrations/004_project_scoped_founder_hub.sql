-- Migration 004: Project-scoped Founder Hub — durable storage shape
--
-- Founder Hub (conversations, messages, runs, checkpoints, tool calls,
-- approvals, run events, run stream events) is scoped to an explicit
-- Project going forward. This migration is Expand-only: it adds nullable
-- `project_id` columns to every named durable artifact plus a `scope_state`
-- enum + CHECK on `agent_conversation.conversations` (the primary Hub
-- artifact). Pre-existing rows are marked LEGACY_UNSCOPED — never derived
-- from title, timestamp, agent profile or workspace ordering (spec
-- docs/superpowers/specs/2026-09-11-project-scoped-founder-hub-design.md).
--
-- `agent_conversation.run_stream_events` additionally gains `workspace_id`
-- (it previously only carried `conversation_id`/`run_id`) so scoped fanout
-- queries do not need to join back to `conversations` for tenant isolation.

-- 1. agent_conversation.conversations — project_id + scope_state (the only
--    table where a scope_state enum + CHECK is meaningful, since it's the
--    root Hub artifact every other artifact hangs off of).
ALTER TABLE agent_conversation.conversations
    ADD COLUMN IF NOT EXISTS project_id character varying(64),
    ADD COLUMN IF NOT EXISTS scope_state character varying(32);

UPDATE agent_conversation.conversations
SET scope_state = 'LEGACY_UNSCOPED'
WHERE scope_state IS NULL;

ALTER TABLE agent_conversation.conversations
    ALTER COLUMN scope_state SET DEFAULT 'LEGACY_UNSCOPED',
    ALTER COLUMN scope_state SET NOT NULL;

ALTER TABLE agent_conversation.conversations
    DROP CONSTRAINT IF EXISTS chk_agent_conversation_conversations_scope_state,
    ADD CONSTRAINT chk_agent_conversation_conversations_scope_state
        CHECK (scope_state IN ('PROJECT_SCOPED', 'LEGACY_UNSCOPED'));

ALTER TABLE agent_conversation.conversations
    DROP CONSTRAINT IF EXISTS chk_agent_conversation_conversations_project_scope,
    ADD CONSTRAINT chk_agent_conversation_conversations_project_scope
        CHECK (
            (scope_state = 'PROJECT_SCOPED' AND project_id IS NOT NULL)
            OR (scope_state = 'LEGACY_UNSCOPED' AND project_id IS NULL)
        );

CREATE INDEX IF NOT EXISTS idx_agent_conversation_conversations_project
    ON agent_conversation.conversations USING btree (workspace_id, project_id, archived_at);

-- 2. agent_conversation.messages — project_id (nullable, no independent
--    scope_state; a message's scope always follows its parent conversation).
ALTER TABLE agent_conversation.messages
    ADD COLUMN IF NOT EXISTS project_id character varying(64);

-- 3. agent.runs — project_id (nullable). Pre-existing rows keep NULL, matching
--    the LEGACY_UNSCOPED convention without needing a duplicate enum column.
ALTER TABLE agent.runs
    ADD COLUMN IF NOT EXISTS project_id character varying(64);

CREATE INDEX IF NOT EXISTS idx_agent_runs_project
    ON agent.runs USING btree (workspace_id, project_id, status, created_at DESC);

-- 4. agent.run_checkpoints — project_id.
ALTER TABLE agent.run_checkpoints
    ADD COLUMN IF NOT EXISTS project_id character varying(64);

-- 5. agent.run_tool_calls — project_id.
ALTER TABLE agent.run_tool_calls
    ADD COLUMN IF NOT EXISTS project_id character varying(64);

-- 6. agent.approvals — project_id.
ALTER TABLE agent.approvals
    ADD COLUMN IF NOT EXISTS project_id character varying(64);

-- 7. agent.run_events — project_id.
ALTER TABLE agent.run_events
    ADD COLUMN IF NOT EXISTS project_id character varying(64);

-- 8. agent_conversation.run_stream_events — workspace_id (new tenant column)
--    + project_id.
ALTER TABLE agent_conversation.run_stream_events
    ADD COLUMN IF NOT EXISTS workspace_id character varying(64),
    ADD COLUMN IF NOT EXISTS project_id character varying(64);

CREATE INDEX IF NOT EXISTS idx_run_stream_events_project
    ON agent_conversation.run_stream_events USING btree (workspace_id, project_id, sequence);
