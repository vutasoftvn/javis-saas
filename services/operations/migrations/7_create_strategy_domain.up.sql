-- Phase 2: Strategy & Startup Co-Founder Methodology Domain

CREATE TABLE IF NOT EXISTS strategy.stage_policies (
    id BIGSERIAL PRIMARY KEY,
    company_id BIGINT NOT NULL,
    workspace_id BIGINT NOT NULL,
    stage_key VARCHAR(50) NOT NULL,
    requirements JSONB NOT NULL DEFAULT '[]',
    minimum_evidence_score DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    blocking_risk_rules JSONB NOT NULL DEFAULT '[]',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

CREATE INDEX idx_stage_policies_company_workspace ON strategy.stage_policies(company_id, workspace_id);
CREATE INDEX idx_stage_policies_stage_key ON strategy.stage_policies(stage_key);

CREATE TABLE IF NOT EXISTS strategy.stage_transitions (
    id BIGSERIAL PRIMARY KEY,
    company_id BIGINT NOT NULL,
    workspace_id BIGINT NOT NULL,
    from_stage VARCHAR(50) NOT NULL,
    to_stage VARCHAR(50) NOT NULL,
    policy_id BIGINT REFERENCES strategy.stage_policies(id) ON DELETE SET NULL,
    allowed BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

CREATE INDEX idx_stage_transitions_company_workspace ON strategy.stage_transitions(company_id, workspace_id);

CREATE TABLE IF NOT EXISTS strategy.assumptions (
    id BIGSERIAL PRIMARY KEY,
    company_id BIGINT NOT NULL,
    workspace_id BIGINT NOT NULL,
    project_id BIGINT NOT NULL REFERENCES strategy.projects(id) ON DELETE CASCADE,
    statement TEXT NOT NULL,
    importance INTEGER NOT NULL DEFAULT 1,
    uncertainty INTEGER NOT NULL DEFAULT 1,
    risk_score DOUBLE PRECISION NOT NULL DEFAULT 1.0,
    status VARCHAR(50) NOT NULL DEFAULT 'untested',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

CREATE INDEX idx_assumptions_company_workspace ON strategy.assumptions(company_id, workspace_id);
CREATE INDEX idx_assumptions_project ON strategy.assumptions(project_id);

CREATE TABLE IF NOT EXISTS strategy.experiments (
    id BIGSERIAL PRIMARY KEY,
    company_id BIGINT NOT NULL,
    workspace_id BIGINT NOT NULL,
    project_id BIGINT NOT NULL REFERENCES strategy.projects(id) ON DELETE CASCADE,
    assumption_id BIGINT REFERENCES strategy.assumptions(id) ON DELETE SET NULL,
    hypothesis TEXT NOT NULL,
    method TEXT NOT NULL,
    success_criteria TEXT NOT NULL,
    budget DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    owner_workforce_member_id BIGINT,
    status VARCHAR(50) NOT NULL DEFAULT 'draft',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

CREATE INDEX idx_experiments_company_workspace ON strategy.experiments(company_id, workspace_id);
CREATE INDEX idx_experiments_project ON strategy.experiments(project_id);
CREATE INDEX idx_experiments_assumption ON strategy.experiments(assumption_id);

CREATE TABLE IF NOT EXISTS strategy.evidence (
    id BIGSERIAL PRIMARY KEY,
    company_id BIGINT NOT NULL,
    workspace_id BIGINT NOT NULL,
    experiment_id BIGINT REFERENCES strategy.experiments(id) ON DELETE SET NULL,
    project_id BIGINT NOT NULL REFERENCES strategy.projects(id) ON DELETE CASCADE,
    source_type VARCHAR(50) NOT NULL,
    claim TEXT NOT NULL,
    strength DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    confidence DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    supports_or_refutes VARCHAR(20) NOT NULL DEFAULT 'supports',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

CREATE INDEX idx_evidence_company_workspace ON strategy.evidence(company_id, workspace_id);
CREATE INDEX idx_evidence_project ON strategy.evidence(project_id);
CREATE INDEX idx_evidence_experiment ON strategy.evidence(experiment_id);

CREATE TABLE IF NOT EXISTS strategy.interviews (
    id BIGSERIAL PRIMARY KEY,
    company_id BIGINT NOT NULL,
    workspace_id BIGINT NOT NULL,
    project_id BIGINT NOT NULL REFERENCES strategy.projects(id) ON DELETE CASCADE,
    contact_ref BIGINT,
    notes TEXT NOT NULL,
    conducted_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

CREATE INDEX idx_interviews_company_workspace ON strategy.interviews(company_id, workspace_id);
CREATE INDEX idx_interviews_project ON strategy.interviews(project_id);

CREATE TABLE IF NOT EXISTS strategy.discovery_signals (
    id BIGSERIAL PRIMARY KEY,
    company_id BIGINT NOT NULL,
    workspace_id BIGINT NOT NULL,
    project_id BIGINT NOT NULL REFERENCES strategy.projects(id) ON DELETE CASCADE,
    signal_type VARCHAR(50) NOT NULL,
    payload JSONB NOT NULL DEFAULT '{}',
    source TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

CREATE INDEX idx_discovery_signals_company_workspace ON strategy.discovery_signals(company_id, workspace_id);
CREATE INDEX idx_discovery_signals_project ON strategy.discovery_signals(project_id);

CREATE TABLE IF NOT EXISTS strategy.gate_evaluations (
    id BIGSERIAL PRIMARY KEY,
    company_id BIGINT NOT NULL,
    workspace_id BIGINT NOT NULL,
    project_id BIGINT NOT NULL REFERENCES strategy.projects(id) ON DELETE CASCADE,
    stage_policy_id BIGINT REFERENCES strategy.stage_policies(id) ON DELETE SET NULL,
    requirements_met BOOLEAN NOT NULL DEFAULT FALSE,
    evidence_score DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    blocking_risks JSONB NOT NULL DEFAULT '[]',
    result VARCHAR(50) NOT NULL DEFAULT 'pending',
    rationale TEXT NOT NULL DEFAULT '',
    human_override BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

CREATE INDEX idx_gate_evaluations_company_workspace ON strategy.gate_evaluations(company_id, workspace_id);
CREATE INDEX idx_gate_evaluations_project ON strategy.gate_evaluations(project_id);

CREATE TABLE IF NOT EXISTS strategy.decision_records (
    id BIGSERIAL PRIMARY KEY,
    company_id BIGINT NOT NULL,
    workspace_id BIGINT NOT NULL,
    project_id BIGINT NOT NULL REFERENCES strategy.projects(id) ON DELETE CASCADE,
    gate_evaluation_id BIGINT REFERENCES strategy.gate_evaluations(id) ON DELETE SET NULL,
    decision VARCHAR(50) NOT NULL,
    actor_workforce_member_id BIGINT,
    evidence_snapshot JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

CREATE INDEX idx_decision_records_company_workspace ON strategy.decision_records(company_id, workspace_id);
CREATE INDEX idx_decision_records_project ON strategy.decision_records(project_id);

CREATE TABLE IF NOT EXISTS strategy.next_action_candidates (
    id BIGSERIAL PRIMARY KEY,
    company_id BIGINT NOT NULL,
    workspace_id BIGINT NOT NULL,
    project_id BIGINT NOT NULL REFERENCES strategy.projects(id) ON DELETE CASCADE,
    source VARCHAR(50) NOT NULL,
    score DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    rationale TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

CREATE INDEX idx_next_action_candidates_company_workspace ON strategy.next_action_candidates(company_id, workspace_id);
CREATE INDEX idx_next_action_candidates_project ON strategy.next_action_candidates(project_id);

CREATE TABLE IF NOT EXISTS strategy.next_action_rankings (
    id BIGSERIAL PRIMARY KEY,
    company_id BIGINT NOT NULL,
    workspace_id BIGINT NOT NULL,
    project_id BIGINT NOT NULL REFERENCES strategy.projects(id) ON DELETE CASCADE,
    candidate_id BIGINT NOT NULL REFERENCES strategy.next_action_candidates(id) ON DELETE CASCADE,
    rank INTEGER NOT NULL,
    llm_rerank_note TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

CREATE INDEX idx_next_action_rankings_company_workspace ON strategy.next_action_rankings(company_id, workspace_id);
CREATE INDEX idx_next_action_rankings_project ON strategy.next_action_rankings(project_id);
