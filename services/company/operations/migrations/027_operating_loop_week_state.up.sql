-- Migration 027: Weekly operating-loop state machine — 2026-09-14 foundation
-- correctness remediation, Task 5.
--
-- 1) `operating.cycle_week_events` — timeline append-only cho advance/close
--    tuần (WEEK_CLOSED, WEEK_ADVANCED, CYCLE_COMPLETED). Không có UPDATE/DELETE
--    path ở tầng service — chỉ INSERT.
-- 2) Unique index phòng thủ trên weekly_plans(cycle_id, week_no) (chỉ áp cho
--    row còn sống) — chốt bất biến "đúng 1 weekly_plans mỗi tuần trong 1
--    cycle" mà auto-materialization (createCycleAuthorized) + state machine
--    advance phụ thuộc vào. Trước migration này không có ràng buộc DB nào
--    chặn duplicate row cho cùng (cycle_id, week_no).
CREATE TABLE operating.cycle_week_events (
  id bigint PRIMARY KEY,
  workspace_id bigint NOT NULL,
  project_id bigint NOT NULL REFERENCES strategy.projects(id) ON DELETE CASCADE,
  cycle_id bigint NOT NULL REFERENCES operating.twelve_week_cycles(id) ON DELETE CASCADE,
  week_no integer NOT NULL,
  event_type varchar(32) NOT NULL,
  actor_id bigint,
  expected_current_week integer NOT NULL,
  payload jsonb,
  occurred_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX ix_cycle_week_events_ws_project_cycle_occurred
  ON operating.cycle_week_events (workspace_id, project_id, cycle_id, occurred_at);

CREATE UNIQUE INDEX uix_weekly_plans_cycle_week_alive
  ON operating.weekly_plans (cycle_id, week_no)
  WHERE deleted_at IS NULL;
