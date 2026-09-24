-- 006_core_identity_projection.down.sql
-- Chỉ chạy được khi mọi user còn hashed_password và mọi workspace có owner_user_id hợp lệ.
ALTER TABLE cosa.workspaces
  ADD CONSTRAINT platform_workspaces_owner_user_id_fkey
  FOREIGN KEY (owner_user_id) REFERENCES cosa.users(id) ON DELETE CASCADE;

ALTER TABLE cosa.users
  ALTER COLUMN hashed_password SET NOT NULL;
