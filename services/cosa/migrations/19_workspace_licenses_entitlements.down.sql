-- services/cosa/migrations/19_workspace_licenses_entitlements.down.sql
DROP TABLE IF EXISTS cosa.platform_workspace_sync_log;
DROP TABLE IF EXISTS cosa.workspace_entitlements;
DROP TABLE IF EXISTS cosa.workspace_licenses;
