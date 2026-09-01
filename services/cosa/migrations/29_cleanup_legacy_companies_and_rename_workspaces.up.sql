-- Migration 29: Cleanup Legacy Company Tables and Rename Platform Workspaces to Canonical Workspaces
-- migration-compat: allow-destructive M2 plan drops legacy company tables replaced by canonical workspaces

-- 1. Drop legacy company tables (cascade to clean up any legacy FKs)
DROP TABLE IF EXISTS cosa.company_agent_policy CASCADE;
DROP TABLE IF EXISTS cosa.company_entitlements CASCADE;
DROP TABLE IF EXISTS cosa.company_memberships CASCADE;
DROP TABLE IF EXISTS cosa.licenses CASCADE;
DROP TABLE IF EXISTS cosa.companies CASCADE;

-- 2. Rename platform_workspaces -> workspaces
ALTER TABLE IF EXISTS cosa.platform_workspaces RENAME TO workspaces;

-- 3. Rename platform_workspace_memberships -> workspace_memberships
ALTER TABLE IF EXISTS cosa.platform_workspace_memberships RENAME TO workspace_memberships;

-- 4. Rename platform_workspace_sync_log -> workspace_sync_log
ALTER TABLE IF EXISTS cosa.platform_workspace_sync_log RENAME TO workspace_sync_log;
