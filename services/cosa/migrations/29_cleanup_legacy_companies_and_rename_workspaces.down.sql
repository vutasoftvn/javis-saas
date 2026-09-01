-- Rollback Migration 29

ALTER TABLE IF EXISTS cosa.workspace_sync_log RENAME TO platform_workspace_sync_log;
ALTER TABLE IF EXISTS cosa.workspace_memberships RENAME TO platform_workspace_memberships;
ALTER TABLE IF EXISTS cosa.workspaces RENAME TO platform_workspaces;
