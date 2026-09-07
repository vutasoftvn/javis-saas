-- Migration 028 Rollback
DROP POLICY IF EXISTS local_upload_tickets_workspace_isolation ON agent.local_upload_tickets;
DROP TABLE IF EXISTS agent.local_upload_tickets;
