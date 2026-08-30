-- packages/agent/migrations/021_skill_candidates_persistence.sql
-- Durable workspace-scoped candidate store and feedback records

CREATE TABLE IF NOT EXISTS agent_skill_candidates (
    candidate_id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    parent_run_id TEXT NOT NULL,
    skill_id TEXT NOT NULL,
    proposed_skill JSONB NOT NULL,
    evidence_refs JSONB NOT NULL DEFAULT '[]'::jsonb,
    eval_score DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    status TEXT NOT NULL DEFAULT 'CANDIDATE',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_agent_skill_candidates_ws
    ON agent_skill_candidates (workspace_id, status);

CREATE TABLE IF NOT EXISTS agent_skill_feedback (
    feedback_id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    skill_id TEXT NOT NULL,
    version TEXT,
    success BOOLEAN NOT NULL DEFAULT true,
    rating INTEGER,
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_agent_skill_feedback_ws_skill
    ON agent_skill_feedback (workspace_id, skill_id);
