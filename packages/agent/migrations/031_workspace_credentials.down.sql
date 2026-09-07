-- Migration 031 Rollback
DROP POLICY IF EXISTS workspace_credentials_workspace_isolation ON models.workspace_credentials;
DROP TABLE IF EXISTS models.workspace_credentials;
