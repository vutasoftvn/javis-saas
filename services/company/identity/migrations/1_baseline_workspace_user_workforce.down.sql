-- Rollback 1_baseline_workspace_user_workforce.up.sql
DROP TABLE IF EXISTS core.workforce_members CASCADE;
DROP TABLE IF EXISTS core.workspace_memberships CASCADE;
DROP TABLE IF EXISTS core.user_projections CASCADE;
DROP TABLE IF EXISTS core.workspaces CASCADE;
