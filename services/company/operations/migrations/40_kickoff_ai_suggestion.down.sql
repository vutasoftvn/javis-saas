ALTER TABLE strategy.project_operating_setups
  DROP COLUMN IF EXISTS ai_suggestion_status,
  DROP COLUMN IF EXISTS ai_suggestion_run_id,
  DROP COLUMN IF EXISTS ai_suggested_outcome,
  DROP COLUMN IF EXISTS ai_suggested_actions,
  DROP COLUMN IF EXISTS ai_suggestion_requested_at;
