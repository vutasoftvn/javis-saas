-- Migration 027: Weekly operating-loop state machine — 2026-09-14 foundation
-- correctness remediation, Task 5.
--
-- 1) `operating.cycle_week_events` — timeline append-only cho advance/close
--    tuần (WEEK_CLOSED, WEEK_ADVANCED, CYCLE_COMPLETED). Không có UPDATE/DELETE
--    path ở tầng service — chỉ INSERT.
-- 2) Unique index phòng thủ trên weekly_plans(cycle_id, week_no) (chỉ áp cho
--    row còn sống) — chốt tường minh bất biến "đúng 1 weekly_plans mỗi tuần
--    trong 1 cycle" mà auto-materialization (createCycleAuthorized) + state
--    machine advance phụ thuộc vào. Review 2026-09-14 phát hiện
--    `uix_weekly_plan_cycle_week` (migration 003_restore_upsert_constraints,
--    UNIQUE (cycle_id, week_no) — KHÔNG partial, áp cho mọi row kể cả đã
--    soft-delete) đã tồn tại từ trước và trên thực tế đã luôn chặn cứng mọi
--    INSERT trùng (cycle_id, week_no) ở tầng DB — nghĩa là dữ liệu thật
--    không thể nào đã có duplicate row sống trước migration này (xác minh
--    bằng thực nghiệm: cố insert 1 row trùng vào DB có index đó bị Postgres
--    từ chối ngay). `uix_weekly_plans_cycle_week_alive` ở đây do đó là lớp
--    phòng thủ bổ sung/tường minh hoá ý định (rõ ràng gắn với "còn sống"),
--    không phải vá 1 lỗ hổng đã từng bị khai thác thật.
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

-- Self-healing trước khi tạo unique index: trước bản fix này,
-- createWeeklyPlanAuthorized là INSERT trần không có bảo vệ trùng lặp, lộ ra
-- qua route public createWeeklyPlanApi (project.week.write.v1) — nếu bất kỳ
-- workspace thật nào từng double-submit route đó cho cùng (cycle_id,
-- week_no) TRƯỚC khi migration này chạy, đã có thể tồn tại row trùng sống
-- trong dữ liệu thật, khiến CREATE UNIQUE INDEX bên dưới fail thẳng khi
-- deploy (không có kiểu "IF NOT EXISTS" nào dung thứ vi phạm constraint).
-- Dedup ở đây chọn "survivor" là row có `id` lớn nhất (Snowflake ID tăng đơn
-- điệu theo thời gian tạo trong repo này — xem
-- shared/services/snowflake.service.ts) tức là row MỚI NHẤT trong nhóm cùng
-- (cycle_id, week_no) còn sống; các row cũ hơn bị soft-delete (set
-- deleted_at) chứ KHÔNG bị xoá cứng — không âm thầm phá dữ liệu, cùng
-- nguyên tắc với cách down-migration 026 xử lý tường minh trạng thái không
-- an toàn thay vì giả định dữ liệu sạch.
WITH ranked AS (
  SELECT
    id,
    ROW_NUMBER() OVER (
      PARTITION BY cycle_id, week_no
      ORDER BY id DESC
    ) AS rn
  FROM operating.weekly_plans
  WHERE deleted_at IS NULL
)
UPDATE operating.weekly_plans wp
SET deleted_at = now(), updated_at = now()
FROM ranked
WHERE wp.id = ranked.id
  AND ranked.rn > 1;

CREATE UNIQUE INDEX uix_weekly_plans_cycle_week_alive
  ON operating.weekly_plans (cycle_id, week_no)
  WHERE deleted_at IS NULL;
