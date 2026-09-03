ALTER TABLE operating.twelve_week_cycles
  ADD CONSTRAINT fk_twelve_week_cycles_project_id
  FOREIGN KEY (project_id) REFERENCES strategy.projects(id) ON DELETE SET NULL;

ALTER TABLE operating.tasks
  ADD CONSTRAINT fk_tasks_weekly_commitment_id
  FOREIGN KEY (weekly_commitment_id) REFERENCES operating.weekly_commitments(id) ON DELETE SET NULL;
