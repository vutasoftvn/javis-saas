-- P1 Task 7 (durable hierarchical supervisor): child-task edges trên
-- scheduled_tasks. Tái dùng claim/fence/DLQ hiện có — không bảng riêng.
-- Bảng execution scheduler CHẠY TẠI LOCAL Workspace Runtime Node
-- (ADR-LOCAL-FIRST-001 §Execution-plane rule), không phải platform VPS.
ALTER TABLE control_plane.scheduled_tasks
  ADD COLUMN IF NOT EXISTS parent_task_id TEXT,
  ADD COLUMN IF NOT EXISTS child_id       TEXT,
  ADD COLUMN IF NOT EXISTS depends_on     JSONB NOT NULL DEFAULT '[]'::jsonb,
  ADD COLUMN IF NOT EXISTS join_policy    TEXT,
  ADD COLUMN IF NOT EXISTS join_quorum    INTEGER,
  ADD COLUMN IF NOT EXISTS child_result   JSONB,
  ADD COLUMN IF NOT EXISTS completion_key TEXT;

CREATE INDEX IF NOT EXISTS idx_scheduled_tasks_parent
  ON control_plane.scheduled_tasks (parent_task_id)
  WHERE parent_task_id IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS uq_scheduled_tasks_parent_child
  ON control_plane.scheduled_tasks (parent_task_id, child_id)
  WHERE parent_task_id IS NOT NULL;
