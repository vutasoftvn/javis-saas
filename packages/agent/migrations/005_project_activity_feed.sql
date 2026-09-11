-- Migration 005: Project Activity projection (Task 3, plan
-- 2026-09-11-project-scoped-founder-hub) — durable, append-only,
-- sequence-numbered, idempotent projection of runtime facts scoped to a
-- Project. Expand-only: three brand-new tables, no ALTER of existing ones.
--
-- This is the durable source of truth the Activity Feed read API (Task 5)
-- will read from — NOT a live-fanout mechanism (that stays
-- agent_conversation.run_stream_events / CosaEventStreamManager, migration
-- 011). `project_activity_events` must never contain raw prompt/content/
-- Vault/tool payload columns — only summary/classification/payload_hash
-- (redacted allowlist, built by apps/cosa/project_activity/service.py).

-- 1. Idempotency claim table — INSERT ... ON CONFLICT DO NOTHING is the
--    atomic "claim" primitive PostgresProjectActivityRepository.append_if_absent
--    relies on: a duplicate (workspace_id, project_id, idempotency_key)
--    delivery never wins the INSERT, so it never reaches the sequence
--    cursor below.
CREATE TABLE IF NOT EXISTS agent.project_activity_idempotency (
    workspace_id character varying(64) NOT NULL,
    project_id character varying(64) NOT NULL,
    idempotency_key character varying(256) NOT NULL,
    event_id character varying(64) NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (workspace_id, project_id, idempotency_key)
);

-- 2. Sequence cursor table — exactly one row per (workspace_id, project_id),
--    incremented via UPDATE ... SET last_sequence = last_sequence + 1
--    RETURNING, which row-locks for the duration of the transaction and
--    serializes concurrent claims for the same Project.
CREATE TABLE IF NOT EXISTS agent.project_activity_sequences (
    workspace_id character varying(64) NOT NULL,
    project_id character varying(64) NOT NULL,
    last_sequence bigint NOT NULL DEFAULT 0,
    PRIMARY KEY (workspace_id, project_id)
);

-- 3. The projection itself — append-only, redacted. `idempotency_key` is
--    intentionally NOT a column here (it lives only in
--    project_activity_idempotency); this table never carries the raw
--    dedup key, keeping the safe-vocabulary event vocabulary the only thing
--    readers of this table ever see.
CREATE TABLE IF NOT EXISTS agent.project_activity_events (
    event_id character varying(64) PRIMARY KEY,
    workspace_id character varying(64) NOT NULL,
    project_id character varying(64) NOT NULL,
    project_sequence bigint NOT NULL,
    kind character varying(64) NOT NULL,
    phase character varying(32),
    status character varying(32),
    actor_kind character varying(32),
    actor_id character varying(128),
    correlation_id character varying(128),
    source_type character varying(32) NOT NULL,
    source_id character varying(128) NOT NULL,
    source_version character varying(64) NOT NULL,
    summary jsonb NOT NULL DEFAULT '{}'::jsonb,
    classification character varying(32) NOT NULL DEFAULT 'internal',
    payload_hash character varying(128),
    occurred_at timestamptz NOT NULL,
    recorded_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (workspace_id, project_id, project_sequence)
);

CREATE INDEX IF NOT EXISTS idx_project_activity_events_project
    ON agent.project_activity_events USING btree (workspace_id, project_id, project_sequence);
