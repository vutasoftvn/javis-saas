DROP INDEX IF EXISTS operating.idx_tasks_key_result_id;
DROP INDEX IF EXISTS operating.idx_tasks_weekly_plan_id;

ALTER TABLE operating.twelve_week_cycles
  DROP COLUMN IF EXISTS source_objective_id;

ALTER TABLE operating.tasks
  DROP COLUMN IF EXISTS key_result_id,
  DROP COLUMN IF EXISTS weekly_plan_id;
