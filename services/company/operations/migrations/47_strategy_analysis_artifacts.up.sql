-- Migration 47: Strategy Analysis Artifacts (PESTEL, Resource/Capability, SWOT)

CREATE TABLE IF NOT EXISTS strategy.pestel_signals (
  id                    BIGINT PRIMARY KEY,
  workspace_id          BIGINT NOT NULL REFERENCES core.workspaces(id) ON DELETE CASCADE,
  strategic_objective_id BIGINT NOT NULL,
  dimension             TEXT NOT NULL CHECK (dimension IN ('POLITICAL', 'ECONOMIC', 'SOCIAL', 'TECHNOLOGICAL', 'ENVIRONMENTAL', 'LEGAL')),
  statement             TEXT NOT NULL,
  impact                TEXT NOT NULL CHECK (impact IN ('HIGH', 'MEDIUM', 'LOW', 'POSITIVE', 'NEGATIVE')),
  certainty             TEXT NOT NULL CHECK (certainty IN ('HIGH', 'MEDIUM', 'LOW')),
  evidence_refs         JSONB NOT NULL DEFAULT '[]'::jsonb,
  bsc_perspectives      JSONB NOT NULL DEFAULT '[]'::jsonb,
  status                TEXT NOT NULL DEFAULT 'DRAFT' CHECK (status IN ('DRAFT', 'ACTIVE', 'ARCHIVED')),
  created_by_member_id  BIGINT,
  updated_by_member_id  BIGINT,
  revision              INTEGER NOT NULL DEFAULT 1,
  created_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT fk_pestel_signals_objective FOREIGN KEY (strategic_objective_id, workspace_id)
    REFERENCES strategy.strategic_objectives (id, workspace_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_pestel_signals_objective_status
  ON strategy.pestel_signals (workspace_id, strategic_objective_id, status);

CREATE TABLE IF NOT EXISTS strategy.resource_capability_assessments (
  id                    BIGINT PRIMARY KEY,
  workspace_id          BIGINT NOT NULL REFERENCES core.workspaces(id) ON DELETE CASCADE,
  strategic_objective_id BIGINT NOT NULL,
  category              TEXT NOT NULL CHECK (category IN (
    'FINANCIAL_RESOURCE',
    'HUMAN_ORGANIZATIONAL_CAPABILITY',
    'INTELLECTUAL_DATA_IP_ASSET',
    'TECHNOLOGY_OPERATIONAL_ASSET',
    'MARKET_RELATIONSHIP_ASSET',
    'GOVERNANCE_LEGAL_RISK_CAPABILITY'
  )),
  statement             TEXT NOT NULL,
  strength_level        TEXT NOT NULL CHECK (strength_level IN ('STRONG', 'ADEQUATE', 'WEAK')),
  evidence_refs         JSONB NOT NULL DEFAULT '[]'::jsonb,
  bsc_perspectives      JSONB NOT NULL DEFAULT '[]'::jsonb,
  status                TEXT NOT NULL DEFAULT 'DRAFT' CHECK (status IN ('DRAFT', 'ACTIVE', 'ARCHIVED')),
  created_by_member_id  BIGINT,
  updated_by_member_id  BIGINT,
  revision              INTEGER NOT NULL DEFAULT 1,
  created_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT fk_resource_assessments_objective FOREIGN KEY (strategic_objective_id, workspace_id)
    REFERENCES strategy.strategic_objectives (id, workspace_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_resource_assessments_objective_status
  ON strategy.resource_capability_assessments (workspace_id, strategic_objective_id, status);

CREATE TABLE IF NOT EXISTS strategy.swot_items (
  id                    BIGINT PRIMARY KEY,
  workspace_id          BIGINT NOT NULL REFERENCES core.workspaces(id) ON DELETE CASCADE,
  strategic_objective_id BIGINT NOT NULL,
  kind                  TEXT NOT NULL CHECK (kind IN ('STRENGTH', 'WEAKNESS', 'OPPORTUNITY', 'THREAT')),
  statement             TEXT NOT NULL,
  source_type           TEXT NOT NULL CHECK (source_type IN ('PESTEL_SIGNAL', 'RESOURCE_CAPABILITY', 'MANUAL')),
  source_id             BIGINT,
  evidence_refs         JSONB NOT NULL DEFAULT '[]'::jsonb,
  bsc_perspectives      JSONB NOT NULL DEFAULT '[]'::jsonb,
  status                TEXT NOT NULL DEFAULT 'DRAFT' CHECK (status IN ('DRAFT', 'ACTIVE', 'ARCHIVED')),
  created_by_member_id  BIGINT,
  updated_by_member_id  BIGINT,
  revision              INTEGER NOT NULL DEFAULT 1,
  created_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT fk_swot_items_objective FOREIGN KEY (strategic_objective_id, workspace_id)
    REFERENCES strategy.strategic_objectives (id, workspace_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_swot_items_objective_status
  ON strategy.swot_items (workspace_id, strategic_objective_id, status);

CREATE INDEX IF NOT EXISTS idx_swot_items_source
  ON strategy.swot_items (workspace_id, source_type, source_id);
