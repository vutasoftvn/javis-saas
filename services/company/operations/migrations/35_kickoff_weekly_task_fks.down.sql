ALTER TABLE operating.tasks
  DROP CONSTRAINT IF EXISTS fk_tasks_weekly_commitment_id;

ALTER TABLE operating.twelve_week_cycles
  DROP CONSTRAINT IF EXISTS fk_twelve_week_cycles_project_id;
