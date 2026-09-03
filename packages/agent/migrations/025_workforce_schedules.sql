-- Migration: 025_workforce_schedules.sql
-- Description: Persist thật cho lịch chạy định kỳ của 1 AI worker trong
-- Workforce org-chart (functional_key + cron_expression). Trước migration
-- này, POST/GET /agent/workforce/schedules* trả response giả (in-memory,
-- không insert DB) — client tạo lịch xong GET lại thấy rỗng. Thực thi
-- (run-now / cron trigger) CHƯA được hỗ trợ ở migration này vì functional_key
-- chưa nối vào execution runtime thật (packages/agent/workforce/catalog.py).

CREATE TABLE IF NOT EXISTS agent.workforce_schedules (
    schedule_id UUID PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    name TEXT NOT NULL,
    functional_key TEXT NOT NULL,
    cron_expression TEXT NOT NULL,
    input_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    configured_by TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('ACTIVE','RETIRED')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    retired_at TIMESTAMPTZ NULL
);

CREATE INDEX IF NOT EXISTS idx_workforce_schedules_ws_status ON agent.workforce_schedules (workspace_id, status);
