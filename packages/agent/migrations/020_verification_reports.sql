-- 020_verification_reports.sql
--
-- Báo cáo kiểm tra tiêu chí hoàn thành (Dự án B): kết luận PASS/FAIL/INCONCLUSIVE của Verifier cho
-- một run của agent. Bằng chứng kiểm toán, không lưu nội dung đầu ra (chỉ băm).
-- Chỉ Expand, idempotent. Lọc workspace_id tường minh trong WHERE (không RLS, theo mẫu 017).
CREATE TABLE IF NOT EXISTS agent.verification_reports (
  report_id text PRIMARY KEY,
  workspace_id text NOT NULL,
  project_id text,
  task_id text NOT NULL,
  run_id text NOT NULL,
  verifier_run_id text,
  verdict text NOT NULL CHECK (verdict IN ('PASS', 'FAIL', 'INCONCLUSIVE')),
  mode text NOT NULL CHECK (mode IN ('deterministic', 'deterministic+judge')),
  criteria_results jsonb NOT NULL DEFAULT '[]'::jsonb,
  criteria_hash text NOT NULL,
  output_hash text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT uix_verification_reports_ws_run UNIQUE (workspace_id, run_id)
);
CREATE INDEX IF NOT EXISTS idx_verification_reports_ws_task
  ON agent.verification_reports (workspace_id, task_id, created_at DESC);
