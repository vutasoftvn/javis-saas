-- Rollback 003_cosa_automation_mvp.sql
ALTER TABLE agent.approvals DROP COLUMN IF EXISTS manifest_hash;
DROP TABLE IF EXISTS agent.automation_run_manifests;
