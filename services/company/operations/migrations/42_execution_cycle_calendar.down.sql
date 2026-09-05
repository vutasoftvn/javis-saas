-- services/company/operations/migrations/42_execution_cycle_calendar.down.sql

DROP TABLE IF EXISTS operating.cycle_revisions CASCADE;

ALTER TABLE operating.tasks
  DROP COLUMN IF EXISTS revision,
  DROP COLUMN IF EXISTS source_revision,
  DROP COLUMN IF EXISTS source_action_id;

ALTER TABLE operating.weekly_commitments
  DROP COLUMN IF EXISTS revision,
  DROP COLUMN IF EXISTS source_revision,
  DROP COLUMN IF EXISTS source_action_id;

ALTER TABLE strategy.project_operating_setups
  DROP COLUMN IF EXISTS cycle_duration_weeks;

ALTER TABLE operating.twelve_week_cycles
  DROP COLUMN IF EXISTS calendar_state,
  DROP COLUMN IF EXISTS revision,
  DROP COLUMN IF EXISTS end_local_date_exclusive,
  DROP COLUMN IF EXISTS start_local_date,
  DROP COLUMN IF EXISTS timezone,
  DROP COLUMN IF EXISTS display_name;
