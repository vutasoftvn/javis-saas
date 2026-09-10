-- Rollback for 002_restore_knowledge_artifact_automation.sql
DROP SCHEMA IF EXISTS knowledge CASCADE;
DROP SCHEMA IF EXISTS agent_artifact CASCADE;
DROP TABLE IF EXISTS agent.automation_run_manifests;
ALTER TABLE agent.approvals DROP COLUMN IF EXISTS manifest_hash;
