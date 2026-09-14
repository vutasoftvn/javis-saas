-- Down 027 — chỉ an toàn TRƯỚC khi có dữ liệu production thật (đúng như ghi
-- chú rollback trong plan). Không cho phép âm thầm xoá timeline đã có sự kiện
-- thật — nếu `cycle_week_events` đã có row, dừng lại tường minh thay vì xoá
-- audit history để "cho tiện" (cùng nguyên tắc với down migration 026).
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM operating.cycle_week_events) THEN
    RAISE EXCEPTION 'Cannot roll back migration 027: cycle_week_events has rows. Events are never dropped — use a forward corrective migration instead.';
  END IF;
END $$;

DROP INDEX IF EXISTS operating.uix_weekly_plans_cycle_week_alive;
DROP TABLE IF EXISTS operating.cycle_week_events;
