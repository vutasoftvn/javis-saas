-- migration-compat: allow-destructive evidence=docs/runbooks/evidence/cosa-007-rename-workspace-to-organization.md
-- Đổi tên workspace -> organization cho lớp danh tính chiếu từ backend/core (spec §2, phạm vi COSA).
-- Chỉ đổi tên bảng/cột; ràng buộc, index và dữ liệu giữ nguyên (id vẫn là id organization của core).
ALTER TABLE cosa.workspaces RENAME TO organizations;
ALTER TABLE cosa.organizations RENAME COLUMN workspace_name TO organization_name;

ALTER TABLE cosa.workspace_memberships RENAME TO organization_memberships;
ALTER TABLE cosa.organization_memberships RENAME COLUMN platform_workspace_id TO organization_id;

ALTER TABLE cosa.workspace_invitations RENAME TO organization_invitations;
ALTER TABLE cosa.organization_invitations RENAME COLUMN workspace_id TO organization_id;
