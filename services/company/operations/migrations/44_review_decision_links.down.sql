-- services/company/operations/migrations/44_review_decision_links.down.sql

DROP INDEX IF EXISTS strategy.idx_next_best_actions_project_status;

ALTER TABLE operating.weekly_commitments
  DROP COLUMN IF EXISTS decision_id;

ALTER TABLE operating.weekly_plans
  DROP COLUMN IF EXISTS decision_id;

ALTER TABLE strategy.next_best_actions
  DROP COLUMN IF EXISTS revision,
  DROP COLUMN IF EXISTS decision_id,
  DROP COLUMN IF EXISTS project_id;

ALTER TABLE strategy.weekly_reviews
  DROP COLUMN IF EXISTS revision,
  DROP COLUMN IF EXISTS decision_ids,
  DROP COLUMN IF EXISTS weekly_plan_ids;
