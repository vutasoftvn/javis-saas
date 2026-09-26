-- 006_membership_session_not_before.up.sql
--
-- Plan 2026-09-25 core-auth Task 4 (session epoch): mốc thời gian mà mọi local
-- session có auth_time cũ hơn không còn được dùng cho membership này. Đặt khi
-- membership bị thu hồi (event Core hoặc tombstone từ sync) và giữ nguyên khi được
-- cấp lại — token cấp trước lần thu hồi không "sống lại" khi membership active trở
-- lại; phải đăng nhập/đồng bộ lại để có quan sát Core mới.
-- Expand-only: cột nullable, không backfill, không đổi hành vi row cũ.
ALTER TABLE core.workspace_memberships
  ADD COLUMN IF NOT EXISTS session_not_before TIMESTAMPTZ;
