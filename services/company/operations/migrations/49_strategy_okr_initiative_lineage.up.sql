-- Migration 49: Strategy OKR and Initiative Lineage, Governance and Composite Integrity

-- 1. Ensure composite uniqueness on strategy.tows_options and strategy.key_results
ALTER TABLE strategy.tows_options
  ADD CONSTRAINT uix_tows_options_id_workspace UNIQUE (id, workspace_id);

ALTER TABLE strategy.key_results
  ADD CONSTRAINT uix_key_results_id_workspace UNIQUE (id, workspace_id);

-- 2. Extend strategy.okr_objectives with lineage and publication columns
ALTER TABLE strategy.okr_objectives
  ADD COLUMN IF NOT EXISTS tows_option_id BIGINT,
  ADD COLUMN IF NOT EXISTS published_by_member_id BIGINT,
  ADD COLUMN IF NOT EXISTS published_at TIMESTAMPTZ;

ALTER TABLE strategy.okr_objectives
  ADD CONSTRAINT fk_okr_objectives_strategic_objective FOREIGN KEY (strategic_objective_id, workspace_id)
    REFERENCES strategy.strategic_objectives (id, workspace_id) ON DELETE SET NULL,
  ADD CONSTRAINT fk_okr_objectives_tows_option FOREIGN KEY (tows_option_id, workspace_id)
    REFERENCES strategy.tows_options (id, workspace_id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_okr_objectives_tows_option
  ON strategy.okr_objectives (workspace_id, tows_option_id);

-- 3. Extend strategy.initiatives with strategy lineage, outcome, dates, and approval columns
ALTER TABLE strategy.initiatives
  ADD CONSTRAINT uix_initiatives_id_workspace UNIQUE (id, workspace_id);

ALTER TABLE strategy.initiatives
  ADD COLUMN IF NOT EXISTS strategic_objective_id BIGINT,
  ADD COLUMN IF NOT EXISTS source_tows_option_id BIGINT,
  ADD COLUMN IF NOT EXISTS description TEXT,
  ADD COLUMN IF NOT EXISTS intended_outcome TEXT,
  ADD COLUMN IF NOT EXISTS start_date TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS target_date TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS milestones JSONB NOT NULL DEFAULT '[]'::jsonb,
  ADD COLUMN IF NOT EXISTS approval_status TEXT NOT NULL DEFAULT 'DRAFT'
    CHECK (approval_status IN ('DRAFT', 'PENDING_APPROVAL', 'APPROVED', 'REJECTED', 'CLOSED')),
  ADD COLUMN IF NOT EXISTS approved_by_member_id BIGINT,
  ADD COLUMN IF NOT EXISTS approved_at TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS decision_id BIGINT REFERENCES strategy.decision_records(id) ON DELETE SET NULL,
  ADD COLUMN IF NOT EXISTS settings_revision INTEGER,
  ADD COLUMN IF NOT EXISTS revision INTEGER NOT NULL DEFAULT 1;

ALTER TABLE strategy.initiatives
  ADD CONSTRAINT fk_initiatives_strategic_objective FOREIGN KEY (strategic_objective_id, workspace_id)
    REFERENCES strategy.strategic_objectives (id, workspace_id) ON DELETE SET NULL,
  ADD CONSTRAINT fk_initiatives_tows_option FOREIGN KEY (source_tows_option_id, workspace_id)
    REFERENCES strategy.tows_options (id, workspace_id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_initiatives_objective_approval
  ON strategy.initiatives (workspace_id, strategic_objective_id, approval_status);

-- 4. Create strategy.initiative_key_results junction table with composite primary key and workspace validation
CREATE TABLE IF NOT EXISTS strategy.initiative_key_results (
  workspace_id   BIGINT NOT NULL REFERENCES core.workspaces(id) ON DELETE CASCADE,
  initiative_id  BIGINT NOT NULL,
  key_result_id  BIGINT NOT NULL,
  created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  PRIMARY KEY (workspace_id, initiative_id, key_result_id),
  CONSTRAINT fk_initiative_key_results_initiative FOREIGN KEY (initiative_id, workspace_id)
    REFERENCES strategy.initiatives (id, workspace_id) ON DELETE CASCADE,
  CONSTRAINT fk_initiative_key_results_key_result FOREIGN KEY (key_result_id, workspace_id)
    REFERENCES strategy.key_results (id, workspace_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_initiative_key_results_initiative
  ON strategy.initiative_key_results (workspace_id, initiative_id);

CREATE INDEX IF NOT EXISTS idx_initiative_key_results_kr
  ON strategy.initiative_key_results (workspace_id, key_result_id);
