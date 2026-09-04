-- WGA #2 — kill-switch per-workspace cho vòng thực thi tự động (workspace_task_sweep).
-- Đặt ở company DB (cùng nơi với tasks) thay vì workspace_agent_policy của
-- services/cosa: task nền headless không mint được control-plane delegation để
-- đọc policy snapshot bên đó. Founder tắt = sweep bỏ qua workspace (task vẫn
-- materialize, chỉ không tự chạy).
CREATE TABLE operating.workspace_execution_settings (
  workspace_id   BIGINT PRIMARY KEY,
  sweep_enabled  BOOLEAN NOT NULL DEFAULT true,
  updated_by     BIGINT,
  updated_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);
