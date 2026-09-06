-- Rollback Migration 49

DROP TABLE IF EXISTS strategy.initiative_key_results CASCADE;

ALTER TABLE strategy.initiatives
  DROP CONSTRAINT IF EXISTS fk_initiatives_tows_option,
  DROP CONSTRAINT IF EXISTS fk_initiatives_strategic_objective,
  DROP CONSTRAINT IF EXISTS uix_initiatives_id_workspace,
  DROP COLUMN IF EXISTS strategic_objective_id,
  DROP COLUMN IF EXISTS source_tows_option_id,
  DROP COLUMN IF EXISTS description,
  DROP COLUMN IF EXISTS intended_outcome,
  DROP COLUMN IF EXISTS start_date,
  DROP COLUMN IF EXISTS target_date,
  DROP COLUMN IF EXISTS milestones,
  DROP COLUMN IF EXISTS approval_status,
  DROP COLUMN IF EXISTS approved_by_member_id,
  DROP COLUMN IF EXISTS approved_at,
  DROP COLUMN IF EXISTS decision_id,
  DROP COLUMN IF EXISTS settings_revision,
  DROP COLUMN IF EXISTS revision;

DROP INDEX IF EXISTS strategy.idx_initiatives_objective_approval;

ALTER TABLE strategy.okr_objectives
  DROP CONSTRAINT IF EXISTS fk_okr_objectives_tows_option,
  DROP CONSTRAINT IF EXISTS fk_okr_objectives_strategic_objective,
  DROP COLUMN IF EXISTS tows_option_id,
  DROP COLUMN IF EXISTS published_by_member_id,
  DROP COLUMN IF EXISTS published_at;

DROP INDEX IF EXISTS strategy.idx_okr_objectives_tows_option;

ALTER TABLE strategy.key_results
  DROP CONSTRAINT IF EXISTS uix_key_results_id_workspace;

ALTER TABLE strategy.tows_options
  DROP CONSTRAINT IF EXISTS uix_tows_options_id_workspace;
