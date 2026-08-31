-- Migration 16: MVP Marketing Contracts (Objectives, Experiments, Learnings, Metrics, Attributions, Decisions, Proposals)

-- Make campaign budget nullable
ALTER TABLE commercial.marketing_campaigns ALTER COLUMN budget DROP NOT NULL;
ALTER TABLE commercial.marketing_campaigns ALTER COLUMN budget DROP DEFAULT;

-- 1. Marketing Objectives
CREATE TABLE IF NOT EXISTS commercial.marketing_objectives (
    id BIGSERIAL PRIMARY KEY,
    workspace_id BIGINT NOT NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    status VARCHAR(50) NOT NULL DEFAULT 'active',
    target_metric VARCHAR(100),
    target_value DOUBLE PRECISION,
    current_value DOUBLE PRECISION,
    start_date TIMESTAMPTZ,
    end_date TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_marketing_objectives_workspace ON commercial.marketing_objectives(workspace_id);

-- 2. Marketing Experiments
CREATE TABLE IF NOT EXISTS commercial.marketing_experiments (
    id BIGSERIAL PRIMARY KEY,
    workspace_id BIGINT NOT NULL,
    campaign_id BIGINT REFERENCES commercial.marketing_campaigns(id) ON DELETE SET NULL,
    name VARCHAR(255) NOT NULL,
    hypothesis TEXT NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'draft',
    baseline_metric VARCHAR(100),
    baseline_value DOUBLE PRECISION,
    target_metric VARCHAR(100),
    target_value DOUBLE PRECISION,
    actual_value DOUBLE PRECISION,
    conclusion TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_marketing_experiments_workspace ON commercial.marketing_experiments(workspace_id);

-- 3. Marketing Learnings
CREATE TABLE IF NOT EXISTS commercial.marketing_learnings (
    id BIGSERIAL PRIMARY KEY,
    workspace_id BIGINT NOT NULL,
    experiment_id BIGINT REFERENCES commercial.marketing_experiments(id) ON DELETE SET NULL,
    title VARCHAR(255) NOT NULL,
    insight TEXT NOT NULL,
    impact VARCHAR(50) NOT NULL DEFAULT 'medium',
    action_items JSONB NOT NULL DEFAULT '[]',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_marketing_learnings_workspace ON commercial.marketing_learnings(workspace_id);

-- 4. Marketing Metric Definitions
CREATE TABLE IF NOT EXISTS commercial.marketing_metric_definitions (
    id BIGSERIAL PRIMARY KEY,
    workspace_id BIGINT NOT NULL,
    name VARCHAR(100) NOT NULL,
    unit VARCHAR(50) NOT NULL DEFAULT 'count',
    description TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (workspace_id, name)
);

CREATE INDEX IF NOT EXISTS idx_marketing_metric_defs_workspace ON commercial.marketing_metric_definitions(workspace_id);

-- 5. Marketing Metric Observations
CREATE TABLE IF NOT EXISTS commercial.marketing_metric_observations (
    id BIGSERIAL PRIMARY KEY,
    workspace_id BIGINT NOT NULL,
    metric_id BIGINT REFERENCES commercial.marketing_metric_definitions(id) ON DELETE CASCADE,
    provider_key TEXT NOT NULL,
    source_record_id TEXT NOT NULL,
    payload_hash TEXT NOT NULL,
    observed_at TIMESTAMPTZ NOT NULL,
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    value DOUBLE PRECISION NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}',
    UNIQUE (workspace_id, provider_key, source_record_id, payload_hash)
);

CREATE INDEX IF NOT EXISTS idx_marketing_metric_obs_workspace ON commercial.marketing_metric_observations(workspace_id, observed_at DESC);

-- 6. Marketing Attributions
CREATE TABLE IF NOT EXISTS commercial.marketing_attributions (
    id BIGSERIAL PRIMARY KEY,
    workspace_id BIGINT NOT NULL,
    campaign_id BIGINT REFERENCES commercial.marketing_campaigns(id) ON DELETE SET NULL,
    channel VARCHAR(100) NOT NULL,
    touchpoint_type VARCHAR(50) NOT NULL,
    conversions DOUBLE PRECISION NOT NULL DEFAULT 0,
    revenue DOUBLE PRECISION NOT NULL DEFAULT 0,
    observed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_marketing_attributions_workspace ON commercial.marketing_attributions(workspace_id);

-- 7. Marketing Decisions
CREATE TABLE IF NOT EXISTS commercial.marketing_decisions (
    id BIGSERIAL PRIMARY KEY,
    workspace_id BIGINT NOT NULL,
    campaign_id BIGINT REFERENCES commercial.marketing_campaigns(id) ON DELETE SET NULL,
    title VARCHAR(255) NOT NULL,
    rationale TEXT NOT NULL,
    decision_type VARCHAR(50) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'active',
    created_by VARCHAR(255) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_marketing_decisions_workspace ON commercial.marketing_decisions(workspace_id);

-- 8. Marketing Proposals
CREATE TABLE IF NOT EXISTS commercial.marketing_proposals (
    id BIGSERIAL PRIMARY KEY,
    workspace_id BIGINT NOT NULL,
    title VARCHAR(255) NOT NULL,
    proposal_type VARCHAR(50) NOT NULL,
    origin VARCHAR(50) NOT NULL CHECK (origin IN ('USER', 'MODEL_DRAFT')),
    status VARCHAR(50) NOT NULL CHECK (status IN ('DRAFT', 'IN_REVIEW', 'APPROVED', 'REJECTED')),
    source_refs JSONB NOT NULL DEFAULT '[]',
    body JSONB NOT NULL DEFAULT '{}',
    created_by VARCHAR(255) NOT NULL,
    reviewed_by VARCHAR(255),
    reviewed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_marketing_proposals_workspace ON commercial.marketing_proposals(workspace_id, status);
