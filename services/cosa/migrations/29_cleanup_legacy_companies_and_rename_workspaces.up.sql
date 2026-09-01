-- Migration 29: Cleanup Legacy Company Tables and Rename Platform Workspaces to Canonical Workspaces
--
-- Task 8 (2026-09-02): migration này CHƯA được apply lên bất kỳ môi trường
-- prod/staging thật nào — `docs/operations/deployment.md` xác nhận "Deploy
-- thật lên staging/prod: CHƯA", `docs/operations/migrations.md` Gate G/F đều
-- "( ) CHƯA chạy". Vì vậy free-form comment cũ không còn đủ để tự cấp phép:
-- exemption phải trỏ tới evidence file thật, được `scripts/check-migration-backward-compat.mjs`
-- verify cấu trúc (không verify giá trị checksum/timestamp thật — operator điền
-- tay trước khi deploy thật, xem file evidence để biết field nào còn placeholder).
-- migration-compat: allow-destructive evidence=docs/runbooks/evidence/m2-destructive-cutover-29.md

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
