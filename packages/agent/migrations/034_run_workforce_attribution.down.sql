-- Down migration 034.
DROP INDEX IF EXISTS agent.idx_agent_runs_wf_employee;
DROP INDEX IF EXISTS agent.idx_agent_runs_wf_attempt;

ALTER TABLE agent.runs
    DROP COLUMN IF EXISTS wf_work_attempt_id,
    DROP COLUMN IF EXISTS wf_work_package_id,
    DROP COLUMN IF EXISTS wf_assignment_id,
    DROP COLUMN IF EXISTS wf_agent_instance_id;
