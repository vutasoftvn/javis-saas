-- 006_core_identity_projection.up.sql
-- Cutover COSA sang backend/core: cosa.users / cosa.workspaces trở thành BẢN CHIẾU (projection)
-- của user và organization ở core. id lấy từ core (snowflake bigint), tự upsert khi user đăng
-- nhập bằng access token của core. Mật khẩu và chủ sở hữu do core quyết định.

-- Mật khẩu chỉ còn ở core; user chiếu từ core không có hash cục bộ.
ALTER TABLE cosa.users
  ALTER COLUMN hashed_password DROP NOT NULL;

-- Chủ sở hữu organization lấy từ core; user chủ sở hữu có thể chưa từng đăng nhập vào COSA
-- nên chưa có dòng trong cosa.users.
ALTER TABLE cosa.workspaces
  DROP CONSTRAINT IF EXISTS platform_workspaces_owner_user_id_fkey;
