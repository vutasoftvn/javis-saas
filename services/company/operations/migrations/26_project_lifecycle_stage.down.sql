-- Revert M4 §3.

DROP TABLE IF EXISTS strategy.project_stage_transitions;
DROP TABLE IF EXISTS strategy.project_stage_transition_policies;

ALTER TABLE strategy.projects DROP CONSTRAINT IF EXISTS projects_status_chk;
ALTER TABLE strategy.projects ALTER COLUMN status SET DEFAULT 'active';
UPDATE strategy.projects SET status = lower(status);

ALTER TABLE strategy.projects DROP CONSTRAINT IF EXISTS projects_lifecycle_stage_chk;
ALTER TABLE strategy.projects ALTER COLUMN lifecycle_stage DROP NOT NULL;
ALTER TABLE strategy.projects ALTER COLUMN lifecycle_stage DROP DEFAULT;
ALTER TABLE strategy.projects
  DROP COLUMN IF EXISTS stage_version,
  DROP COLUMN IF EXISTS stage_entered_at;
ALTER TABLE strategy.projects RENAME COLUMN lifecycle_stage TO phase;
