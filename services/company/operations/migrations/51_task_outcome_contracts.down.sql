-- 51_task_outcome_contracts.down.sql
-- Gỡ Outcome Contract. An toàn N-1: chỉ xóa object do 51 tạo.

ALTER TABLE operating.tasks
  DROP COLUMN IF EXISTS active_outcome_contract_id;

DROP TABLE IF EXISTS operating.task_outcome_kr_links;
DROP TABLE IF EXISTS operating.task_outcome_contracts;
