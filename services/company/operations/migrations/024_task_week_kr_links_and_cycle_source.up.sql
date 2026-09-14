-- Migration 024: Task liên kết trực tiếp Week/KR (nullable); Cycle ghi
-- nguồn Objective sinh ra nó (dùng bởi OKR→Weekly generator, Task 5).
ALTER TABLE operating.tasks
  ADD COLUMN weekly_plan_id bigint REFERENCES operating.weekly_plans(id) ON DELETE SET NULL,
  ADD COLUMN key_result_id bigint REFERENCES strategy.key_results(id) ON DELETE SET NULL;

ALTER TABLE operating.twelve_week_cycles
  ADD COLUMN source_objective_id bigint REFERENCES strategy.okr_objectives(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_tasks_weekly_plan_id ON operating.tasks(weekly_plan_id) WHERE weekly_plan_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_tasks_key_result_id ON operating.tasks(key_result_id) WHERE key_result_id IS NOT NULL;
