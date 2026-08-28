-- services/company/commercial/migrations/9_marketing_context_hybrid.up.sql
-- Nâng cấp marketing_contexts sang schema lai (hybrid relational + jsonb) với revision, status, provenance

ALTER TABLE commercial.marketing_contexts ADD COLUMN IF NOT EXISTS revision INTEGER NOT NULL DEFAULT 1;
ALTER TABLE commercial.marketing_contexts ADD COLUMN IF NOT EXISTS status TEXT NOT NULL DEFAULT 'draft';
ALTER TABLE commercial.marketing_contexts ADD COLUMN IF NOT EXISTS updated_by_user_id BIGINT;
ALTER TABLE commercial.marketing_contexts ADD COLUMN IF NOT EXISTS reviewed_by_user_id BIGINT;
ALTER TABLE commercial.marketing_contexts ADD COLUMN IF NOT EXISTS reviewed_at TIMESTAMPTZ;
ALTER TABLE commercial.marketing_contexts ADD COLUMN IF NOT EXISTS source_skill_id VARCHAR(100);
ALTER TABLE commercial.marketing_contexts ADD COLUMN IF NOT EXISTS source_skill_version VARCHAR(50);
ALTER TABLE commercial.marketing_contexts ADD COLUMN IF NOT EXISTS source_skill_hash VARCHAR(64);
ALTER TABLE commercial.marketing_contexts ADD COLUMN IF NOT EXISTS offer_architecture JSONB;
ALTER TABLE commercial.marketing_contexts ADD COLUMN IF NOT EXISTS twelve_week_plan JSONB;

-- Đảm bảo mỗi workspace có duy nhất 1 context canonical
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'uix_marketing_contexts_workspace'
    ) THEN
        ALTER TABLE commercial.marketing_contexts ADD CONSTRAINT uix_marketing_contexts_workspace UNIQUE (workspace_id);
    END IF;
END $$;

-- 1. Bảng lưu trữ revision snapshot bất biến (append-only)
CREATE TABLE IF NOT EXISTS commercial.marketing_context_revisions (
    id BIGINT PRIMARY KEY,
    context_id BIGINT NOT NULL REFERENCES commercial.marketing_contexts(id) ON DELETE CASCADE,
    workspace_id BIGINT NOT NULL,
    revision INTEGER NOT NULL,
    snapshot JSONB NOT NULL,
    created_by_user_id BIGINT,
    source_skill_id VARCHAR(100),
    source_skill_version VARCHAR(50),
    source_skill_hash VARCHAR(64),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_marketing_context_revisions_workspace ON commercial.marketing_context_revisions(workspace_id);
CREATE INDEX IF NOT EXISTS idx_marketing_context_revisions_context ON commercial.marketing_context_revisions(context_id);
CREATE INDEX IF NOT EXISTS idx_marketing_context_revisions_lookup ON commercial.marketing_context_revisions(context_id, revision);

-- 2. Bảng Product Marketing
CREATE TABLE IF NOT EXISTS commercial.marketing_product_marketing (
    id BIGINT PRIMARY KEY,
    context_id BIGINT NOT NULL REFERENCES commercial.marketing_contexts(id) ON DELETE CASCADE,
    workspace_id BIGINT NOT NULL,
    category VARCHAR(255),
    positioning_statement TEXT,
    alternatives JSONB DEFAULT '[]'::jsonb,
    differentiators JSONB DEFAULT '[]'::jsonb,
    brand_voice JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uix_marketing_product_marketing_context UNIQUE (context_id)
);

CREATE INDEX IF NOT EXISTS idx_marketing_product_marketing_workspace ON commercial.marketing_product_marketing(workspace_id);
CREATE INDEX IF NOT EXISTS idx_marketing_product_marketing_context ON commercial.marketing_product_marketing(context_id);

-- 3. Bảng ICP Segments
CREATE TABLE IF NOT EXISTS commercial.marketing_icp_segments (
    id BIGINT PRIMARY KEY,
    context_id BIGINT NOT NULL REFERENCES commercial.marketing_contexts(id) ON DELETE CASCADE,
    workspace_id BIGINT NOT NULL,
    segment TEXT NOT NULL,
    confidence VARCHAR(20) NOT NULL DEFAULT 'medium',
    evidence_ids JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_marketing_icp_segments_workspace ON commercial.marketing_icp_segments(workspace_id);
CREATE INDEX IF NOT EXISTS idx_marketing_icp_segments_context ON commercial.marketing_icp_segments(context_id);

-- 4. Bảng Customer Research Themes
CREATE TABLE IF NOT EXISTS commercial.marketing_customer_research_themes (
    id BIGINT PRIMARY KEY,
    context_id BIGINT NOT NULL REFERENCES commercial.marketing_contexts(id) ON DELETE CASCADE,
    workspace_id BIGINT NOT NULL,
    type VARCHAR(50) NOT NULL,
    summary TEXT NOT NULL,
    confidence VARCHAR(20) NOT NULL DEFAULT 'medium',
    evidence_ids JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_marketing_customer_research_themes_workspace ON commercial.marketing_customer_research_themes(workspace_id);
CREATE INDEX IF NOT EXISTS idx_marketing_customer_research_themes_context ON commercial.marketing_customer_research_themes(context_id);

-- 5. Bảng Customer Language Quotes
CREATE TABLE IF NOT EXISTS commercial.marketing_customer_language (
    id BIGINT PRIMARY KEY,
    context_id BIGINT NOT NULL REFERENCES commercial.marketing_contexts(id) ON DELETE CASCADE,
    workspace_id BIGINT NOT NULL,
    quote TEXT NOT NULL,
    source_id VARCHAR(100),
    captured_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_marketing_customer_language_workspace ON commercial.marketing_customer_language(workspace_id);
CREATE INDEX IF NOT EXISTS idx_marketing_customer_language_context ON commercial.marketing_customer_language(context_id);

-- 6. Bảng Marketing Context Evidence & Provenance
CREATE TABLE IF NOT EXISTS commercial.marketing_context_evidence (
    id BIGINT PRIMARY KEY,
    context_id BIGINT NOT NULL REFERENCES commercial.marketing_contexts(id) ON DELETE CASCADE,
    workspace_id BIGINT NOT NULL,
    evidence_id VARCHAR(100) NOT NULL,
    kind VARCHAR(50) NOT NULL,
    source_url TEXT,
    captured_at TIMESTAMPTZ,
    captured_by VARCHAR(100),
    confidence VARCHAR(20) NOT NULL DEFAULT 'medium',
    trust VARCHAR(20) NOT NULL DEFAULT 'unreviewed',
    sensitivity VARCHAR(20) NOT NULL DEFAULT 'internal',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uix_marketing_context_evidence_id UNIQUE (context_id, evidence_id)
);

CREATE INDEX IF NOT EXISTS idx_marketing_context_evidence_workspace ON commercial.marketing_context_evidence(workspace_id);
CREATE INDEX IF NOT EXISTS idx_marketing_context_evidence_context ON commercial.marketing_context_evidence(context_id);
