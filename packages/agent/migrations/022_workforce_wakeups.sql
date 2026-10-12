-- 022_workforce_wakeups.sql
--
-- Dự án C: sổ cái wakeup của workforce. Một hàng = một lần đánh thức được chấp nhận (đã qua các
-- cổng kiểm tra). Dùng cho dedup theo nguồn, rate cap theo ngày, hop cap và danh sách lý do
-- (coalescing của scheduler chỉ gộp nông nên lý do không đi trong payload).
-- Chỉ Expand, idempotent. Lọc workspace_id tường minh.
CREATE TABLE IF NOT EXISTS agent.workforce_wakeups (
  wake_id text PRIMARY KEY,
  workspace_id text NOT NULL,
  assignment_id text NOT NULL,
  project_id text NOT NULL,
  reason_kind text NOT NULL,
  source_ref text NOT NULL,
  hop integer NOT NULL DEFAULT 0 CHECK (hop >= 0),
  created_at timestamptz NOT NULL DEFAULT now(),
  handled_at timestamptz,
  CONSTRAINT uix_workforce_wakeups_ws_assignment_source UNIQUE (workspace_id, assignment_id, source_ref)
);
CREATE INDEX IF NOT EXISTS idx_workforce_wakeups_ws_assignment_created
  ON agent.workforce_wakeups (workspace_id, assignment_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_workforce_wakeups_unhandled
  ON agent.workforce_wakeups (workspace_id, assignment_id, project_id, created_at)
  WHERE handled_at IS NULL;
