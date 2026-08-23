-- Chuyển 5 bảng identity từ bigserial (auto-increment) sang snowflake ID sinh
-- ở tầng ứng dụng — đúng quy ước db.md. Xoá sạch dữ liệu cũ vì ID serial cũ
-- không còn tương thích với ID sinh mới (theo yêu cầu, không cần giữ lại).
TRUNCATE TABLE core.organizations, core.users, core.workforce_members, core.workspace_members, core.workspaces CASCADE;

ALTER TABLE core.organizations ALTER COLUMN id DROP DEFAULT;
ALTER TABLE core.users ALTER COLUMN id DROP DEFAULT;
ALTER TABLE core.workforce_members ALTER COLUMN id DROP DEFAULT;
ALTER TABLE core.workspace_members ALTER COLUMN id DROP DEFAULT;
ALTER TABLE core.workspaces ALTER COLUMN id DROP DEFAULT;
