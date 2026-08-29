-- services/cosa/migrations/20_backfill_platform_workspaces.down.sql
DELETE FROM cosa.platform_workspace_sync_log
WHERE client_creation_id LIKE 'backfill:company:%';
