-- 020_verification_reports.down.sql
-- Báo cáo là bằng chứng kiểm toán: từ chối rollback khi đã có dữ liệu (theo mẫu 017).
DO $$ BEGIN
  IF EXISTS (SELECT 1 FROM agent.verification_reports) THEN
    RAISE EXCEPTION 'Cannot roll back migration 020: agent.verification_reports contains audit evidence. Use a forward corrective migration instead.';
  END IF;
END $$;
DROP INDEX IF EXISTS agent.idx_verification_reports_ws_task;
DROP TABLE IF EXISTS agent.verification_reports;
