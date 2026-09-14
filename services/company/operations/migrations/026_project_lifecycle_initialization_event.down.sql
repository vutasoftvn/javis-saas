-- Down 026: chỉ khôi phục NOT NULL trên from_stage khi KHÔNG có bất kỳ event
-- PROJECT_INITIALIZED nào — rollback không được phép xoá audit history để
-- "cho tiện". Nếu đã có baseline event thật, rollback phải dừng lại tường
-- minh thay vì âm thầm xoá dữ liệu.
DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM strategy.project_lifecycle_events
    WHERE event_type = 'PROJECT_INITIALIZED'
  ) THEN
    RAISE EXCEPTION 'Cannot roll back migration 026: PROJECT_INITIALIZED events exist and would violate NOT NULL on from_stage. Audit history is not deleted to make rollback convenient.';
  END IF;
END $$;

ALTER TABLE strategy.project_lifecycle_events
  DROP COLUMN initialization_source,
  DROP COLUMN event_type,
  ALTER COLUMN from_stage SET NOT NULL;
