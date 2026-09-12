-- Migration 008: Governed Skill Improvement Feedback Loop
--
-- Adds durable substrate for:
-- 1. Skill usage observations pinned to exact (skill_id, version, definition_hash) per run
-- 2. Windowed feedback aggregates with monotonic revisions
-- 3. Durable improvement requests with at most one live request per exact identity
-- 4. Durable improvement outbox for runless worker scheduling
-- 5. Isolated evaluation and mutation lineage evidence tables
-- 6. Extends agent_skill_feedback with exact identity, run reference, and idempotency key

CREATE TABLE IF NOT EXISTS agent.skill_usage_observations (
    observation_id varchar(64) PRIMARY KEY,
    workspace_id varchar(64) NOT NULL,
    run_id varchar(128) NOT NULL REFERENCES agent.runs(run_id) ON DELETE RESTRICT,
    skill_id varchar(256) NOT NULL,
    skill_version varchar(64) NOT NULL,
    definition_hash varchar(128) NOT NULL,
    root_spec_id varchar(256) NOT NULL,
    root_definition_hash varchar(128) NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (run_id, skill_id, skill_version, definition_hash)
);

CREATE TABLE IF NOT EXISTS agent.skill_feedback_aggregates (
    workspace_id varchar(64) NOT NULL,
    skill_id varchar(256) NOT NULL,
    skill_version varchar(64) NOT NULL,
    definition_hash varchar(128) NOT NULL,
    revision integer NOT NULL,
    sample_count integer NOT NULL,
    aggregate_score double precision NOT NULL,
    previous_score double precision,
    degradation_delta double precision,
    window_started_at timestamptz NOT NULL,
    window_ended_at timestamptz NOT NULL,
    health varchar(32) NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (workspace_id, skill_id, skill_version, definition_hash, revision)
);

CREATE TABLE IF NOT EXISTS agent.skill_improvement_requests (
    request_id varchar(64) PRIMARY KEY,
    workspace_id varchar(64) NOT NULL,
    skill_id varchar(256) NOT NULL,
    skill_version varchar(64) NOT NULL,
    definition_hash varchar(128) NOT NULL,
    trigger varchar(64) NOT NULL,
    feedback_aggregate_revision integer NOT NULL,
    policy_hash varchar(128) NOT NULL,
    status varchar(64) NOT NULL,
    attempt_count integer NOT NULL DEFAULT 0,
    claim_token varchar(128),
    claimed_by varchar(128),
    claimed_at timestamptz,
    safe_reason_code varchar(128),
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS agent.skill_improvement_outbox (
    outbox_id varchar(64) PRIMARY KEY,
    request_id varchar(64) NOT NULL UNIQUE REFERENCES agent.skill_improvement_requests(request_id) ON DELETE RESTRICT,
    workspace_id varchar(64) NOT NULL,
    state varchar(32) NOT NULL,
    attempt_count integer NOT NULL DEFAULT 0,
    next_attempt_at timestamptz NOT NULL DEFAULT now(),
    claim_token varchar(128),
    claimed_by varchar(128),
    delivered_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS agent.skill_improvement_evaluations (
    evaluation_id varchar(64) PRIMARY KEY,
    workspace_id varchar(64) NOT NULL,
    request_id varchar(64) NOT NULL REFERENCES agent.skill_improvement_requests(request_id) ON DELETE RESTRICT,
    candidate_id varchar(128) REFERENCES agent.agent_skill_candidates(candidate_id) ON DELETE SET NULL,
    suite_ref varchar(256) NOT NULL,
    suite_hash varchar(128) NOT NULL,
    baseline_score double precision NOT NULL,
    candidate_score double precision NOT NULL,
    delta double precision NOT NULL,
    passed_cases jsonb DEFAULT '[]'::jsonb NOT NULL,
    failed_cases jsonb DEFAULT '[]'::jsonb NOT NULL,
    safe_reason_code varchar(128),
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS agent.skill_improvement_mutations (
    mutation_id varchar(64) PRIMARY KEY,
    workspace_id varchar(64) NOT NULL,
    request_id varchar(64) NOT NULL REFERENCES agent.skill_improvement_requests(request_id) ON DELETE RESTRICT,
    candidate_id varchar(128) REFERENCES agent.agent_skill_candidates(candidate_id) ON DELETE SET NULL,
    round_no integer NOT NULL,
    mutator_name varchar(128) NOT NULL,
    accepted boolean NOT NULL,
    score_before double precision NOT NULL,
    score_after double precision NOT NULL,
    validation_passed boolean NOT NULL,
    safe_reason_code varchar(128),
    created_at timestamptz NOT NULL DEFAULT now()
);

ALTER TABLE agent.agent_skill_feedback
    ADD COLUMN IF NOT EXISTS skill_version varchar(64),
    ADD COLUMN IF NOT EXISTS definition_hash varchar(128),
    ADD COLUMN IF NOT EXISTS run_id varchar(128) REFERENCES agent.runs(run_id) ON DELETE RESTRICT,
    ADD COLUMN IF NOT EXISTS idempotency_key varchar(128),
    ADD COLUMN IF NOT EXISTS source_kind varchar(32) DEFAULT 'user' NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS ux_agent_skill_feedback_ws_idempotency
ON agent.agent_skill_feedback (workspace_id, idempotency_key)
WHERE idempotency_key IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS ux_agent_skill_improvement_requests_live
ON agent.skill_improvement_requests (workspace_id, skill_id, skill_version, definition_hash)
WHERE status IN ('PENDING', 'RUNNING');

CREATE INDEX IF NOT EXISTS idx_skill_usage_obs_ws_run_skill
ON agent.skill_usage_observations (workspace_id, run_id, skill_id);

CREATE INDEX IF NOT EXISTS idx_skill_feedback_agg_newest
ON agent.skill_feedback_aggregates (workspace_id, skill_id, skill_version, definition_hash, revision DESC);

CREATE INDEX IF NOT EXISTS idx_skill_improvement_requests_claim
ON agent.skill_improvement_requests (status, created_at)
WHERE status = 'PENDING';

CREATE INDEX IF NOT EXISTS idx_skill_improvement_outbox_due
ON agent.skill_improvement_outbox (state, next_attempt_at)
WHERE state IN ('PENDING', 'RETRY');
