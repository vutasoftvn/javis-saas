-- Down 018 — từ chối rollback nếu đã có dòng nào được phân bổ initiative_id.
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM models.run_usage WHERE initiative_id IS NOT NULL) THEN
    RAISE EXCEPTION 'Cannot roll back migration 018: models.run_usage has attributed initiative rows. Use a forward corrective migration instead.';
  END IF;
END $$;

DROP INDEX IF EXISTS models.idx_run_usage_ws_proj_init_time;
ALTER TABLE models.run_usage DROP COLUMN IF EXISTS initiative_id;
