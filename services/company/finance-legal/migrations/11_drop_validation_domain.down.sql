-- Rollback 11_drop_validation_domain.up.sql
CREATE SCHEMA IF NOT EXISTS validation;

CREATE TABLE IF NOT EXISTS validation.validation_hypotheses (
    id BIGINT PRIMARY KEY,
    workspace_id BIGINT NOT NULL,
    project_id BIGINT,
    title VARCHAR(255) NOT NULL,
    statement TEXT NOT NULL,
    confidence_score DOUBLE PRECISION NOT NULL DEFAULT 0.5,
    status VARCHAR(50) NOT NULL DEFAULT 'TESTING',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS validation.validation_experiments (
    id BIGINT PRIMARY KEY,
    workspace_id BIGINT NOT NULL,
    hypothesis_id BIGINT NOT NULL REFERENCES validation.validation_hypotheses(id) ON DELETE CASCADE,
    experiment_type VARCHAR(50) NOT NULL DEFAULT 'INTERVIEW',
    title VARCHAR(255) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'RUNNING',
    start_date TIMESTAMPTZ,
    end_date TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS validation.evidence_items (
    id BIGINT PRIMARY KEY,
    workspace_id BIGINT NOT NULL,
    experiment_id BIGINT NOT NULL REFERENCES validation.validation_experiments(id) ON DELETE CASCADE,
    evidence_type VARCHAR(50) NOT NULL DEFAULT 'QUOTE',
    title VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    strength_score DOUBLE PRECISION NOT NULL DEFAULT 1.0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS validation.customer_interviews (
    id BIGINT PRIMARY KEY,
    workspace_id BIGINT NOT NULL,
    customer_name VARCHAR(255) NOT NULL,
    interview_date TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    key_insights TEXT,
    pain_points TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);
