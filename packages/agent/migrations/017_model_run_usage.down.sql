-- Down 017 — sổ cái usage là dữ liệu tính tiền/quota: không cho xoá âm thầm.
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM models.run_usage) THEN
    RAISE EXCEPTION 'Cannot roll back migration 017: models.run_usage has rows. Use a forward corrective migration instead.';
  END IF;
END $$;

DROP TABLE IF EXISTS models.run_usage;
