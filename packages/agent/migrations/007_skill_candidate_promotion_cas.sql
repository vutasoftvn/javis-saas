-- Migration 007: Skill Candidate Promotion CAS Baseline
--
-- Ensures agent.agent_skill_candidates and agent.agent_skill_feedback exist
-- with exact CAS columns for safe, idempotent promotion of custom skills.

CREATE TABLE IF NOT EXISTS agent.agent_skill_candidates (
    candidate_id varchar(128) PRIMARY KEY,
    workspace_id varchar(64) NOT NULL,
    parent_run_id varchar(128) NOT NULL,
    skill_id varchar(128) NOT NULL,
    proposed_skill jsonb NOT NULL,
    evidence_refs jsonb DEFAULT '[]'::jsonb NOT NULL,
    eval_score double precision DEFAULT 0.0 NOT NULL,
    status varchar(32) NOT NULL,
    definition_hash varchar(128),
    promotion_approval_id varchar(64),
    promotion_definition_hash varchar(128),
    published_at timestamptz,
    created_at timestamptz DEFAULT now() NOT NULL,
    updated_at timestamptz DEFAULT now() NOT NULL
);

ALTER TABLE agent.agent_skill_candidates
    ADD COLUMN IF NOT EXISTS definition_hash varchar(128),
    ADD COLUMN IF NOT EXISTS promotion_approval_id varchar(64),
    ADD COLUMN IF NOT EXISTS promotion_definition_hash varchar(128),
    ADD COLUMN IF NOT EXISTS published_at timestamptz,
    ADD COLUMN IF NOT EXISTS created_at timestamptz DEFAULT now() NOT NULL,
    ADD COLUMN IF NOT EXISTS updated_at timestamptz DEFAULT now() NOT NULL;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'ux_agent_skill_candidates_ws_candidate'
          AND conrelid = 'agent.agent_skill_candidates'::regclass
    ) THEN
        ALTER TABLE agent.agent_skill_candidates
        ADD CONSTRAINT ux_agent_skill_candidates_ws_candidate UNIQUE (workspace_id, candidate_id);
    END IF;
END $$;

CREATE UNIQUE INDEX IF NOT EXISTS ux_agent_skill_candidates_promotion_approval
ON agent.agent_skill_candidates (promotion_approval_id)
WHERE promotion_approval_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_agent_skill_candidates_ws_skill
ON agent.agent_skill_candidates (workspace_id, skill_id);

CREATE TABLE IF NOT EXISTS agent.agent_skill_feedback (
    feedback_id varchar(64) PRIMARY KEY,
    workspace_id varchar(64) NOT NULL,
    skill_id varchar(128) NOT NULL,
    version varchar(64),
    success boolean DEFAULT true NOT NULL,
    rating integer,
    notes text,
    created_at timestamptz DEFAULT now() NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_agent_skill_feedback_ws_skill
ON agent.agent_skill_feedback (workspace_id, skill_id);
