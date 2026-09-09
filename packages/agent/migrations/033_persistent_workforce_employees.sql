-- Migration 033: Persistent AI employee identity.
--
-- Tạo agent.workforce_employees (identity bền vững theo workspace, không tái
-- sử dụng agent_instance_id) và nối nó vào agent.workforce_assignments qua
-- cột nullable agent_instance_id.
--
-- Expand-only (Encore guardrail #4 tương đương cho Agent Platform):
--   - bảng mới + cột nullable + index, không đổi cột/ràng buộc đã có;
--   - backfill deterministic chỉ cho assignment đang ACTIVE, idempotent
--     (employee_code = 'LEGACY-<assignment UUID>', PK tái dùng chính
--     assignment_id nên chạy lại migration không sinh bản ghi trùng).
-- Run/assignment lịch sử vẫn đọc được; có 033_*.down.sql.

CREATE TABLE IF NOT EXISTS agent.workforce_employees (
    agent_instance_id UUID PRIMARY KEY,
    workspace_id      TEXT NOT NULL,
    employee_code     TEXT NOT NULL,
    display_name      TEXT NOT NULL,
    status            TEXT NOT NULL CHECK (status IN ('ACTIVE','SUSPENDED','RETIRED')),
    created_by        TEXT NOT NULL,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    suspended_at      TIMESTAMPTZ NULL,
    retired_at        TIMESTAMPTZ NULL,
    UNIQUE (workspace_id, employee_code)
);

CREATE INDEX IF NOT EXISTS idx_workforce_employees_ws_status
    ON agent.workforce_employees (workspace_id, status);

ALTER TABLE agent.workforce_assignments
    ADD COLUMN IF NOT EXISTS agent_instance_id UUID NULL;

CREATE INDEX IF NOT EXISTS idx_workforce_assignments_employee
    ON agent.workforce_assignments (workspace_id, agent_instance_id);

-- Backfill: mỗi assignment ACTIVE chưa nối employee nhận 1 employee legacy
-- deterministic (tái dùng assignment_id làm PK employee — UUID không đụng
-- uuid4() sinh mới về sau).
INSERT INTO agent.workforce_employees (
    agent_instance_id, workspace_id, employee_code, display_name, status, created_by, created_at
)
SELECT
    a.assignment_id,
    a.workspace_id,
    'LEGACY-' || a.assignment_id::text,
    'Legacy ' || a.functional_key,
    'ACTIVE',
    'system:migration-033',
    a.created_at
FROM agent.workforce_assignments a
WHERE a.status = 'ACTIVE'
  AND a.agent_instance_id IS NULL
ON CONFLICT (agent_instance_id) DO NOTHING;

UPDATE agent.workforce_assignments a
SET agent_instance_id = a.assignment_id
WHERE a.status = 'ACTIVE'
  AND a.agent_instance_id IS NULL
  AND EXISTS (
      SELECT 1 FROM agent.workforce_employees e
      WHERE e.agent_instance_id = a.assignment_id
  );
