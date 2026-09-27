-- Down 029 — chỉ gỡ cột trạng thái phân rã (không mang dữ liệu nghiệp vụ gốc).
ALTER TABLE operating.weekly_plans
  DROP CONSTRAINT IF EXISTS weekly_plans_decomposition_status_chk;
ALTER TABLE operating.weekly_plans
  DROP COLUMN IF EXISTS decomposition_updated_at,
  DROP COLUMN IF EXISTS decomposition_error_code,
  DROP COLUMN IF EXISTS decomposition_status;
