-- 32_pmf_scoreboards.up.sql
-- Create pmf_scoreboard_runs and maturity_assessments tables for reproducible PMF scoring and maturity tracking

CREATE TABLE IF NOT EXISTS strategy.pmf_scoreboard_runs (
    id BIGINT PRIMARY KEY,
    workspace_id BIGINT NOT NULL,
    project_id BIGINT NOT NULL REFERENCES strategy.projects(id) ON DELETE CASCADE,
    contract_version_ids JSONB NOT NULL DEFAULT '[]'::jsonb,
    input_snapshot_ids JSONB NOT NULL DEFAULT '[]'::jsonb,
    reviewed_evidence_ids JSONB NOT NULL DEFAULT '[]'::jsonb,
    policy_version TEXT NOT NULL DEFAULT 'v1',
    score_components JSONB NOT NULL DEFAULT '[]'::jsonb,
    missing_data_flags JSONB NOT NULL DEFAULT '[]'::jsonb,
    reliability_flags JSONB NOT NULL DEFAULT '[]'::jsonb,
    calculation_hash TEXT NOT NULL,
    result VARCHAR(50) NOT NULL,
    human_review_state JSONB NOT NULL DEFAULT '{}'::jsonb,
    calculated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT pmf_scoreboard_result_chk
        CHECK (result IN ('INSUFFICIENT_DATA', 'MIXED', 'PROMISING', 'CONCERNING'))
);

CREATE INDEX IF NOT EXISTS idx_pmf_scoreboards_ws_proj ON strategy.pmf_scoreboard_runs(workspace_id, project_id);
CREATE INDEX IF NOT EXISTS idx_pmf_scoreboards_hash ON strategy.pmf_scoreboard_runs(calculation_hash);

CREATE TABLE IF NOT EXISTS strategy.maturity_assessments (
    id BIGINT PRIMARY KEY,
    workspace_id BIGINT NOT NULL,
    project_id BIGINT NOT NULL REFERENCES strategy.projects(id) ON DELETE CASCADE,
    scoreboard_run_id BIGINT REFERENCES strategy.pmf_scoreboard_runs(id) ON DELETE SET NULL,
    dimensions JSONB NOT NULL DEFAULT '{}'::jsonb,
    assessed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_maturity_assessments_ws_proj ON strategy.maturity_assessments(workspace_id, project_id);
CREATE INDEX IF NOT EXISTS idx_maturity_assessments_run ON strategy.maturity_assessments(scoreboard_run_id);
