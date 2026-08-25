-- services/company/identity/migrations/5_identity_projection_rework.up.sql

-- core.users -> core.user_projections: Company không còn là credential
-- authority. password_hash và role bị xoá — password chỉ COSA giữ, role chỉ
-- nằm ở membership (một user có thể có role khác nhau ở mỗi workspace).
ALTER TABLE core.users RENAME TO user_projections;
ALTER TABLE core.user_projections DROP COLUMN password_hash;
ALTER TABLE core.user_projections DROP COLUMN role;

-- core.workspace_members -> core.workspace_memberships: track nguồn gốc
-- sync (platform_membership_id, source_updated_at, synced_at) để debug
-- "role này lấy từ đâu, lúc nào", và enforce uniqueness ở DB level để
-- concurrent sync không tạo duplicate membership.
ALTER TABLE core.workspace_members RENAME TO workspace_memberships;
ALTER TABLE core.workspace_memberships ADD COLUMN platform_membership_id TEXT;
ALTER TABLE core.workspace_memberships ADD COLUMN source_updated_at TIMESTAMPTZ;
ALTER TABLE core.workspace_memberships ADD COLUMN synced_at TIMESTAMPTZ;
ALTER TABLE core.workspace_memberships ADD CONSTRAINT workspace_memberships_workspace_user_unique UNIQUE (workspace_id, user_id);
