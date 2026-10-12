-- 021_workforce_reporting_integrity.sql
--
-- Dự án C: toàn vẹn đường báo cáo của workforce. Chỉ Expand, idempotent. Dữ liệu cũ có thể còn
-- cha treo, nên FK ghép đặt NOT VALID (ép cho ghi mới, không quét dữ liệu cũ).
CREATE UNIQUE INDEX IF NOT EXISTS uix_workforce_assignments_id_workspace
  ON agent.workforce_assignments (assignment_id, workspace_id);

CREATE INDEX IF NOT EXISTS idx_workforce_assignments_ws_reports_to
  ON agent.workforce_assignments (workspace_id, reports_to_assignment_id)
  WHERE reports_to_assignment_id IS NOT NULL;

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'chk_workforce_assignments_no_self_report') THEN
    ALTER TABLE agent.workforce_assignments
      ADD CONSTRAINT chk_workforce_assignments_no_self_report
      CHECK (reports_to_assignment_id IS NULL OR reports_to_assignment_id <> assignment_id) NOT VALID;
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_workforce_assignments_reports_to') THEN
    ALTER TABLE agent.workforce_assignments
      ADD CONSTRAINT fk_workforce_assignments_reports_to
      FOREIGN KEY (reports_to_assignment_id, workspace_id)
      REFERENCES agent.workforce_assignments (assignment_id, workspace_id) NOT VALID;
  END IF;
END $$;
