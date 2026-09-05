-- Migration 8 down: drop business permissions tables

DROP TABLE IF EXISTS core.workspace_policy_versions CASCADE;
DROP TABLE IF EXISTS core.member_role_assignments CASCADE;
DROP TABLE IF EXISTS core.role_permissions CASCADE;
DROP TABLE IF EXISTS core.workspace_roles CASCADE;
DROP TABLE IF EXISTS core.permission_definitions CASCADE;
