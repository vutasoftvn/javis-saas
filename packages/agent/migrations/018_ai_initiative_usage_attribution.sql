-- 018_ai_initiative_usage_attribution.sql
--
-- Phân bổ usage LLM theo AI Initiative (Task 5, plan 2026-09-28-stage-adaptive-ai-operating-system).
-- Thêm cột initiative_id (nullable) vào models.run_usage để ghi nhận chi phí/token
-- của từng Initiative cụ thể, phục vụ đo lường ROI và kiểm soát ngân sách.
-- Các run cũ/không có Initiative giữ nguyên NULL (chưa phân bổ), không đoán mò.

ALTER TABLE models.run_usage
  ADD COLUMN IF NOT EXISTS initiative_id text;

CREATE INDEX IF NOT EXISTS idx_run_usage_ws_proj_init_time
  ON models.run_usage (workspace_id, project_id, initiative_id, created_at DESC);
