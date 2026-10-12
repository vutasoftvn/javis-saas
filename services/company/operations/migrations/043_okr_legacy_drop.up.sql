-- 043_okr_legacy_drop.up.sql
-- Dự án A0 (contract, phần hoãn từ 039): xóa họ OKR cũ.
-- migration-compat: allow-destructive evidence=docs/runbooks/evidence/okr-legacy-drop-043.md
--
-- Mọi tham chiếu vào hai bảng cũ đã bị ngắt ở 039 và không còn mã nào dùng chúng. Để không mất
-- bằng chứng, dòng còn lại (nếu có) được sao sang bảng lưu trữ trước khi DROP.
DO $$
BEGIN
  IF to_regclass('strategy.objectives') IS NOT NULL
     AND EXISTS (SELECT 1 FROM strategy.objectives) THEN
    CREATE TABLE IF NOT EXISTS strategy.legacy_objectives_archive AS
      SELECT * FROM strategy.objectives;
  END IF;
  IF to_regclass('strategy.cosa_key_results') IS NOT NULL
     AND EXISTS (SELECT 1 FROM strategy.cosa_key_results) THEN
    CREATE TABLE IF NOT EXISTS strategy.legacy_cosa_key_results_archive AS
      SELECT * FROM strategy.cosa_key_results;
  END IF;
END $$;

DROP FUNCTION IF EXISTS strategy.fn_goals_needing_review;
DROP TABLE IF EXISTS strategy.cosa_key_results;
DROP TABLE IF EXISTS strategy.objectives;
