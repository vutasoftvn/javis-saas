-- Rollback migration 33: Workspace and user module visibility preferences

DROP TABLE IF EXISTS cosa.user_workspace_module_preferences;
DROP TABLE IF EXISTS cosa.workspace_module_configs;
