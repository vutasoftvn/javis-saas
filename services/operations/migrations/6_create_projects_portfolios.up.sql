CREATE TABLE strategy.portfolios (
    id BIGSERIAL PRIMARY KEY,
    workspace_id BIGINT NOT NULL,
    brain_id BIGINT,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    strategic_focus VARCHAR(255),
    status VARCHAR(50) NOT NULL DEFAULT 'active',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

CREATE INDEX idx_portfolios_workspace ON strategy.portfolios(workspace_id);

CREATE TABLE strategy.projects (
    id BIGSERIAL PRIMARY KEY,
    workspace_id BIGINT NOT NULL,
    brain_id BIGINT,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    phase VARCHAR(50),
    current_gate VARCHAR(50),
    status VARCHAR(50) NOT NULL DEFAULT 'active',
    owner_id BIGINT,
    project_type VARCHAR(50),
    strategic_priority VARCHAR(50),
    founder_attention_budget DOUBLE PRECISION,
    portfolio_id BIGINT REFERENCES strategy.portfolios(id) ON DELETE SET NULL,
    start_date TIMESTAMPTZ,
    end_date TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

CREATE INDEX idx_projects_workspace ON strategy.projects(workspace_id);
CREATE INDEX idx_projects_portfolio ON strategy.projects(portfolio_id);

CREATE TABLE strategy.portfolio_projects (
    id BIGSERIAL PRIMARY KEY,
    workspace_id BIGINT NOT NULL,
    portfolio_id BIGINT NOT NULL REFERENCES strategy.portfolios(id) ON DELETE CASCADE,
    project_id BIGINT NOT NULL REFERENCES strategy.projects(id) ON DELETE CASCADE,
    strategic_priority VARCHAR(50) NOT NULL DEFAULT 'core',
    capacity_allocation DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    founder_attention_hours DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ,
    CONSTRAINT uix_portfolio_project UNIQUE (portfolio_id, project_id)
);

CREATE INDEX idx_portfolio_projects_portfolio ON strategy.portfolio_projects(portfolio_id);
CREATE INDEX idx_portfolio_projects_project ON strategy.portfolio_projects(project_id);
