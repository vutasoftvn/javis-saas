-- Migration 034: Durable workforce attribution trên agent.runs (Task 4).
--
-- Run của workforce bắt buộc carry đủ 4 opaque IDs: employee, assignment,
-- work package, work attempt (spec §5.2). Run non-workforce cũ giữ NULL.
-- Expand-only + có 034_*.down.sql.

ALTER TABLE agent.runs
    ADD COLUMN IF NOT EXISTS wf_agent_instance_id UUID NULL,
    ADD COLUMN IF NOT EXISTS wf_assignment_id     UUID NULL,
    ADD COLUMN IF NOT EXISTS wf_work_package_id   TEXT NULL,
    ADD COLUMN IF NOT EXISTS wf_work_attempt_id   TEXT NULL;

CREATE INDEX IF NOT EXISTS idx_agent_runs_wf_attempt
    ON agent.runs (wf_work_attempt_id)
    WHERE wf_work_attempt_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_agent_runs_wf_employee
    ON agent.runs (workspace_id, wf_agent_instance_id)
    WHERE wf_agent_instance_id IS NOT NULL;
