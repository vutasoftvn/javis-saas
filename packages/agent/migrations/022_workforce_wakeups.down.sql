-- 022_workforce_wakeups.down.sql
-- Sổ cái là bằng chứng kiểm toán: từ chối rollback khi đã có dữ liệu (theo mẫu 017/020).
DO $$ BEGIN
  IF EXISTS (SELECT 1 FROM agent.workforce_wakeups) THEN
    RAISE EXCEPTION 'Cannot roll back migration 022: agent.workforce_wakeups contains audit evidence. Use a forward corrective migration instead.';
  END IF;
END $$;
DROP INDEX IF EXISTS agent.idx_workforce_wakeups_unhandled;
DROP INDEX IF EXISTS agent.idx_workforce_wakeups_ws_assignment_created;
DROP TABLE IF EXISTS agent.workforce_wakeups;
