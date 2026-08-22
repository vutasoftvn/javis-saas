CREATE SCHEMA IF NOT EXISTS commercial;

CREATE TABLE commercial.marketing_contexts (
    id BIGSERIAL PRIMARY KEY,
    workspace_id BIGINT NOT NULL,
    category VARCHAR(255),
    market JSONB,
    positioning JSONB,
    pricing JSONB,
    channels JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_marketing_contexts_workspace ON commercial.marketing_contexts(workspace_id);

CREATE TABLE commercial.marketing_campaigns (
    id BIGSERIAL PRIMARY KEY,
    workspace_id BIGINT NOT NULL,
    name VARCHAR(255) NOT NULL,
    funnel_stage VARCHAR(50) NOT NULL DEFAULT 'discover',
    channels JSONB,
    budget DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    status VARCHAR(50) NOT NULL DEFAULT 'draft',
    start_date TIMESTAMPTZ,
    end_date TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_marketing_campaigns_workspace ON commercial.marketing_campaigns(workspace_id);

CREATE TABLE commercial.campaign_assets (
    id BIGSERIAL PRIMARY KEY,
    workspace_id BIGINT NOT NULL,
    campaign_id BIGINT NOT NULL REFERENCES commercial.marketing_campaigns(id) ON DELETE CASCADE,
    asset_type VARCHAR(50) NOT NULL,
    title VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'draft',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_campaign_assets_workspace ON commercial.campaign_assets(workspace_id);
CREATE INDEX idx_campaign_assets_campaign ON commercial.campaign_assets(campaign_id);

CREATE TABLE commercial.marketing_forms (
    id BIGSERIAL PRIMARY KEY,
    workspace_id BIGINT NOT NULL,
    title VARCHAR(255) NOT NULL,
    slug VARCHAR(255) NOT NULL,
    fields_schema JSONB NOT NULL DEFAULT '[]',
    is_published BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uix_marketing_forms_slug UNIQUE (workspace_id, slug)
);

CREATE INDEX idx_marketing_forms_workspace ON commercial.marketing_forms(workspace_id);

CREATE TABLE commercial.marketing_lead_intakes (
    id BIGSERIAL PRIMARY KEY,
    workspace_id BIGINT NOT NULL,
    form_id BIGINT REFERENCES commercial.marketing_forms(id) ON DELETE SET NULL,
    contact_data JSONB NOT NULL DEFAULT '{}',
    source VARCHAR(100),
    status VARCHAR(50) NOT NULL DEFAULT 'new',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_marketing_lead_intakes_workspace ON commercial.marketing_lead_intakes(workspace_id);
