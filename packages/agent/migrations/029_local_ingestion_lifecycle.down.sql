-- Migration 029 Rollback
DROP POLICY IF EXISTS local_ingestion_events_workspace_isolation ON agent.local_ingestion_events;
DROP POLICY IF EXISTS local_ingestion_attempts_workspace_isolation ON agent.local_ingestion_attempts;
DROP TABLE IF EXISTS agent.local_ingestion_events;
DROP TABLE IF EXISTS agent.local_ingestion_attempts;
