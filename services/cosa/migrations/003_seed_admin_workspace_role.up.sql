-- 003_seed_admin_workspace_role.up.sql
--
-- Startup Core Task-2: `cosa.workspace_invitations.role_id` carries a
-- CHECK (role_id IN ('member','admin')) AND a FK to cosa.roles(id), but the
-- 001 role seed (which folded in the deleted 004_seed_canonical_cosa_roles,
-- whose comment drops "legacy" admin) never inserts an 'admin' row — so
-- issuing an invitation with role_id='admin' fails the FK. Restore the row.
-- ADR-WORKSPACE-INVITATION-001 keeps the member/admin invite roles.

INSERT INTO cosa.roles (id, name, category, sort_order, description) VALUES
  ('admin', 'Quản trị workspace', 'system', 14, 'Quản trị viên của một workspace — mời và quản lý thành viên')
ON CONFLICT (id) DO NOTHING;
