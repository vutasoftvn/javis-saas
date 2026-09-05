-- services/company/operations/migrations/44_review_decision_links.up.sql
-- S4: Link weekly reviews, next-best-action proposals, plans, and commitments to decision provenance

ALTER TABLE strategy.weekly_reviews
  ADD COLUMN IF NOT EXISTS weekly_plan_ids JSONB NOT NULL DEFAULT '[]'::jsonb,
  ADD COLUMN IF NOT EXISTS decision_ids JSONB NOT NULL DEFAULT '[]'::jsonb,
  ADD COLUMN IF NOT EXISTS revision INTEGER NOT NULL DEFAULT 1;

ALTER TABLE strategy.next_best_actions
  ADD COLUMN IF NOT EXISTS project_id BIGINT NULL REFERENCES strategy.projects(id) ON DELETE CASCADE,
  ADD COLUMN IF NOT EXISTS decision_id BIGINT NULL REFERENCES strategy.decision_records(id) ON DELETE SET NULL,
  ADD COLUMN IF NOT EXISTS revision INTEGER NOT NULL DEFAULT 1;

ALTER TABLE operating.weekly_plans
  ADD COLUMN IF NOT EXISTS decision_id BIGINT NULL REFERENCES strategy.decision_records(id) ON DELETE SET NULL;

ALTER TABLE operating.weekly_commitments
  ADD COLUMN IF NOT EXISTS decision_id BIGINT NULL REFERENCES strategy.decision_records(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_next_best_actions_project_status
  ON strategy.next_best_actions(project_id, status);
