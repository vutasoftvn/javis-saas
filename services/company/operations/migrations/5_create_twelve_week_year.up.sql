CREATE TABLE operating.twelve_week_cycles (
    id BIGSERIAL PRIMARY KEY,
    workspace_id BIGINT NOT NULL,
    brain_id BIGINT,
    project_id BIGINT,
    theme VARCHAR(255),
    vision_statement TEXT NOT NULL DEFAULT '',
    stage_at_start VARCHAR(50) NOT NULL DEFAULT 'S1_PROBLEM_VALIDATION',
    current_week INT NOT NULL DEFAULT 1,
    duration_weeks INT NOT NULL DEFAULT 12,
    overall_execution_score DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    start_date TIMESTAMPTZ,
    end_date TIMESTAMPTZ,
    commitment_level VARCHAR(50),
    status VARCHAR(50) NOT NULL DEFAULT 'ACTIVE',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

CREATE INDEX idx_twelve_week_cycles_workspace ON operating.twelve_week_cycles(workspace_id);

CREATE TABLE operating.weekly_plans (
    id BIGSERIAL PRIMARY KEY,
    workspace_id BIGINT NOT NULL,
    cycle_id BIGINT NOT NULL REFERENCES operating.twelve_week_cycles(id) ON DELETE CASCADE,
    week_no INT NOT NULL,
    start_date TIMESTAMPTZ,
    end_date TIMESTAMPTZ,
    focus TEXT,
    mission TEXT,
    execution_score DOUBLE PRECISION,
    outcome_score DOUBLE PRECISION,
    reflection TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ,
    CONSTRAINT uix_weekly_plan_cycle_week UNIQUE (cycle_id, week_no)
);

CREATE INDEX idx_weekly_plans_workspace ON operating.weekly_plans(workspace_id);
CREATE INDEX idx_weekly_plans_cycle ON operating.weekly_plans(cycle_id);

CREATE TABLE operating.weekly_commitments (
    id BIGSERIAL PRIMARY KEY,
    workspace_id BIGINT NOT NULL,
    weekly_plan_id BIGINT NOT NULL REFERENCES operating.weekly_plans(id) ON DELETE CASCADE,
    initiative_id BIGINT REFERENCES strategy.initiatives(id) ON DELETE SET NULL,
    title VARCHAR(255) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'todo',
    planned_effort VARCHAR(50),
    commitment_owner_type VARCHAR(50) DEFAULT 'FOUNDER',
    execution_mode VARCHAR(50) DEFAULT 'MANUAL',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

CREATE INDEX idx_weekly_commitments_workspace ON operating.weekly_commitments(workspace_id);
CREATE INDEX idx_weekly_commitments_plan ON operating.weekly_commitments(weekly_plan_id);
