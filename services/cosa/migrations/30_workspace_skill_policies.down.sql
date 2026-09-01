-- Rollback Migration 30 — chỉ dùng trên database disposable, không xử lý
-- production rollback image (dữ liệu policy sẽ mất khi drop bảng này).
DROP TABLE IF EXISTS control_plane.workspace_skill_policies;
