-- Down migration 033: gỡ persistent AI employee identity.
-- An toàn N-1: chỉ xóa object do 033 tạo. Assignment lịch sử vẫn còn
-- (chỉ mất cột liên kết agent_instance_id).

DROP INDEX IF EXISTS agent.idx_workforce_assignments_employee;

ALTER TABLE agent.workforce_assignments
    DROP COLUMN IF EXISTS agent_instance_id;

DROP INDEX IF EXISTS agent.idx_workforce_employees_ws_status;

DROP TABLE IF EXISTS agent.workforce_employees;
