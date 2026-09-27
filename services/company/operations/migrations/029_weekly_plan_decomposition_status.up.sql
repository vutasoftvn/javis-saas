-- Migration 029: trạng thái phân rã mục tiêu tuần (WGA G6) — chỉ Expand.
--
-- Trước đây khi agent phân rã mục tiêu thất bại (provider lỗi, JSON sai schema,
-- lỗi POST execution-plans) worker chỉ ghi log; Command Center chờ một kế hoạch
-- không bao giờ tới. Ba cột nullable dưới đây cho phép UI đọc trạng thái có cấu
-- trúc: 'pending' (vừa yêu cầu), 'done' (đã có plan draft), 'failed' (+ mã lỗi).
-- NULL = weekly plan chưa từng yêu cầu phân rã (dữ liệu cũ giữ nguyên nghĩa).
ALTER TABLE operating.weekly_plans
  ADD COLUMN IF NOT EXISTS decomposition_status text,
  ADD COLUMN IF NOT EXISTS decomposition_error_code text,
  ADD COLUMN IF NOT EXISTS decomposition_updated_at timestamptz;

ALTER TABLE operating.weekly_plans
  DROP CONSTRAINT IF EXISTS weekly_plans_decomposition_status_chk;
ALTER TABLE operating.weekly_plans
  ADD CONSTRAINT weekly_plans_decomposition_status_chk
  CHECK (decomposition_status IS NULL OR decomposition_status IN ('pending', 'done', 'failed'));
