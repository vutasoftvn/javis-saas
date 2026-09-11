-- Rollback for 003_seed_admin_workspace_role.up.sql
DELETE FROM cosa.roles WHERE id = 'admin';
