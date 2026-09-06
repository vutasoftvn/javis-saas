-- Migration 48: TOWS Option Selection, Evaluation, and Lineage

CREATE TABLE IF NOT EXISTS strategy.tows_options (
  id                    BIGINT PRIMARY KEY,
  workspace_id          BIGINT NOT NULL REFERENCES core.workspaces(id) ON DELETE CASCADE,
  strategic_objective_id BIGINT NOT NULL,
  quadrant              TEXT NOT NULL CHECK (quadrant IN ('SO', 'WO', 'ST', 'WT')),
  title                 TEXT NOT NULL,
  rationale             TEXT,
  swot_item_ids         JSONB NOT NULL DEFAULT '[]'::jsonb,
  status                TEXT NOT NULL DEFAULT 'DRAFT' CHECK (status IN ('DRAFT', 'PROPOSED', 'SELECTED', 'REJECTED', 'SUPERSEDED')),
  ai_provenance         JSONB,
  selected_by_member_id BIGINT,
  selected_at           TIMESTAMPTZ,
  decision_id           BIGINT REFERENCES strategy.decision_records(id) ON DELETE SET NULL,
  created_by_member_id  BIGINT,
  updated_by_member_id  BIGINT,
  revision              INTEGER NOT NULL DEFAULT 1,
  created_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT fk_tows_options_objective FOREIGN KEY (strategic_objective_id, workspace_id)
    REFERENCES strategy.strategic_objectives (id, workspace_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_tows_options_objective_status
  ON strategy.tows_options (workspace_id, strategic_objective_id, status);

CREATE TABLE IF NOT EXISTS strategy.tows_option_evaluations (
  id                    BIGINT PRIMARY KEY,
  workspace_id          BIGINT NOT NULL REFERENCES core.workspaces(id) ON DELETE CASCADE,
  tows_option_id        BIGINT NOT NULL REFERENCES strategy.tows_options(id) ON DELETE CASCADE,
  impact_score          INTEGER NOT NULL CHECK (impact_score BETWEEN 1 AND 5),
  difficulty_score      INTEGER NOT NULL CHECK (difficulty_score BETWEEN 1 AND 5),
  rationale             TEXT,
  scored_by_member_id   BIGINT,
  scorer_kind           TEXT NOT NULL DEFAULT 'HUMAN' CHECK (scorer_kind IN ('HUMAN', 'AI_AGENT')),
  created_at            TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_tows_evaluations_option
  ON strategy.tows_option_evaluations (workspace_id, tows_option_id);
