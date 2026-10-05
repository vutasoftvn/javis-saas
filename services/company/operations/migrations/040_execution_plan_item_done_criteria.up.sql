-- Dự án A: tiêu chí hoàn thành có cấu trúc (DoneCriteria v1) cho từng item của execution plan.
-- Chỉ Expand: cột nullable; item cũ giữ NULL (agent nhận "không có tiêu chí").
ALTER TABLE operating.execution_plan_items
  ADD COLUMN IF NOT EXISTS done_criteria jsonb;
