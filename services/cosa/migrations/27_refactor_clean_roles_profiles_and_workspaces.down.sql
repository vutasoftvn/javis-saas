-- services/cosa/migrations/27_refactor_clean_roles_profiles_and_workspaces.down.sql

ALTER TABLE IF EXISTS cosa.workspaces RENAME TO platform_workspaces;
ALTER TABLE IF EXISTS cosa.workspace_memberships RENAME TO platform_workspace_memberships;
ALTER TABLE IF EXISTS cosa.workspace_sync_logs RENAME TO platform_workspace_sync_log;
