-- Migration: 008_agent_evals.sql
-- Description: Durable eval suite/case/run/result + skill candidate/mutation
-- ledger cho Skill Optimization Lab (Wave 5-6). Theo Blueprint V2 §71.2 và
-- COSA_AGENT_PLATFORM_BLUEPRINT_V2_RECONCILED_PLAN_2026-08-24.md Phần G.
--
-- Ghi chú phạm vi: `packages/agent_core/evals/{models,runner}.py` (đã có từ
-- trước, 4 nhóm eval nền tảng theo Master Guide §33) vẫn chạy in-memory, không
-- đổi — schema này bổ sung persistence CHO SKILL EVAL/OPTIMIZATION LAB cụ thể,
-- không phải viết lại runner nền tảng đã có.

CREATE SCHEMA IF NOT EXISTS agent_evals;

CREATE TABLE IF NOT EXISTS agent_evals.suites (
    suite_id VARCHAR(64) PRIMARY KEY,
    name VARCHAR(256) NOT NULL,
    target_kind VARCHAR(32) NOT NULL,  -- "skill" | "agent" | "workflow"
    target_id VARCHAR(128) NOT NULL,
    description TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS agent_evals.cases (
    case_id VARCHAR(64) PRIMARY KEY,
    suite_id VARCHAR(64) NOT NULL REFERENCES agent_evals.suites(suite_id) ON DELETE CASCADE,
    input_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    expected_outcome JSONB NOT NULL DEFAULT '{}'::jsonb,
    is_holdout BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_agent_evals_cases_suite ON agent_evals.cases(suite_id);

CREATE TABLE IF NOT EXISTS agent_evals.runs (
    eval_run_id VARCHAR(64) PRIMARY KEY,
    suite_id VARCHAR(64) NOT NULL REFERENCES agent_evals.suites(suite_id) ON DELETE CASCADE,
    target_kind VARCHAR(32) NOT NULL,
    target_id VARCHAR(128) NOT NULL,
    target_version VARCHAR(32),
    target_definition_hash VARCHAR(64),
    status VARCHAR(32) NOT NULL DEFAULT 'running',
    pass_rate REAL,
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_agent_evals_runs_suite ON agent_evals.runs(suite_id);

CREATE TABLE IF NOT EXISTS agent_evals.results (
    result_id VARCHAR(64) PRIMARY KEY,
    eval_run_id VARCHAR(64) NOT NULL REFERENCES agent_evals.runs(eval_run_id) ON DELETE CASCADE,
    case_id VARCHAR(64) NOT NULL REFERENCES agent_evals.cases(case_id) ON DELETE CASCADE,
    passed BOOLEAN NOT NULL,
    score REAL NOT NULL DEFAULT 0.0,
    details TEXT,
    error_message TEXT,
    evaluated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_agent_evals_results_run ON agent_evals.results(eval_run_id);

-- Skill Optimization Lab (Blueprint V2 §69.3): Candidate Skill -> Executor ->
-- Scorer -> Analyst -> Mutator (1 bounded mutation) -> Challenger eval ->
-- improved? -> revert/keep -> full regression -> approval. KHÔNG tự publish.
CREATE TABLE IF NOT EXISTS agent_evals.skill_candidates (
    candidate_id VARCHAR(64) PRIMARY KEY,
    base_skill_id VARCHAR(128) NOT NULL,
    base_skill_version VARCHAR(32) NOT NULL,
    base_definition_hash VARCHAR(64) NOT NULL,
    proposed_content JSONB NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'candidate',  -- candidate|evaluated|approved|rejected|published
    baseline_score REAL,
    latest_score REAL,
    round_no INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS agent_evals.skill_mutations (
    mutation_id VARCHAR(64) PRIMARY KEY,
    candidate_id VARCHAR(64) NOT NULL REFERENCES agent_evals.skill_candidates(candidate_id) ON DELETE CASCADE,
    round_no INTEGER NOT NULL,
    diff_summary TEXT NOT NULL,
    rationale TEXT,
    pre_score REAL,
    post_score REAL,
    accepted BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_agent_evals_skill_mutations_candidate ON agent_evals.skill_mutations(candidate_id);
