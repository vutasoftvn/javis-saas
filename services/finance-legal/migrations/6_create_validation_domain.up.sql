CREATE SCHEMA IF NOT EXISTS validation;

CREATE TABLE validation.validation_hypotheses (
    id BIGSERIAL PRIMARY KEY,
    workspace_id BIGINT NOT NULL,
    project_id BIGINT,
    title VARCHAR(255) NOT NULL,
    statement TEXT NOT NULL,
    confidence_score DOUBLE PRECISION NOT NULL DEFAULT 0.5,
    status VARCHAR(50) NOT NULL DEFAULT 'TESTING',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_hypotheses_workspace ON validation.validation_hypotheses(workspace_id);

CREATE TABLE validation.validation_experiments (
    id BIGSERIAL PRIMARY KEY,
    workspace_id BIGINT NOT NULL,
    hypothesis_id BIGINT NOT NULL REFERENCES validation.validation_hypotheses(id) ON DELETE CASCADE,
    experiment_type VARCHAR(50) NOT NULL DEFAULT 'INTERVIEW',
    title VARCHAR(255) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'RUNNING',
    start_date TIMESTAMPTZ,
    end_date TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_experiments_workspace ON validation.validation_experiments(workspace_id);
CREATE INDEX idx_experiments_hypothesis ON validation.validation_experiments(hypothesis_id);

CREATE TABLE validation.evidence_items (
    id BIGSERIAL PRIMARY KEY,
    workspace_id BIGINT NOT NULL,
    experiment_id BIGINT NOT NULL REFERENCES validation.validation_experiments(id) ON DELETE CASCADE,
    evidence_type VARCHAR(50) NOT NULL DEFAULT 'QUOTE',
    title VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    strength_score DOUBLE PRECISION NOT NULL DEFAULT 1.0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_evidence_workspace ON validation.evidence_items(workspace_id);
CREATE INDEX idx_evidence_experiment ON validation.evidence_items(experiment_id);

CREATE TABLE validation.customer_interviews (
    id BIGSERIAL PRIMARY KEY,
    workspace_id BIGINT NOT NULL,
    customer_name VARCHAR(255) NOT NULL,
    interview_date TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    key_insights TEXT,
    pain_points TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_customer_interviews_workspace ON validation.customer_interviews(workspace_id);
