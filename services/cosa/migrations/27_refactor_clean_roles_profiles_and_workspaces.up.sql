-- services/cosa/migrations/27_refactor_clean_roles_profiles_and_workspaces.up.sql

-- 1. Chuẩn hóa bảng cosa.roles: bỏ level/scope, thêm name/category
ALTER TABLE cosa.roles ADD COLUMN IF NOT EXISTS name TEXT;
ALTER TABLE cosa.roles ADD COLUMN IF NOT EXISTS category TEXT;

-- Seed dữ liệu cho cột mới nếu có dữ liệu cũ
UPDATE cosa.roles SET name = 'Quản trị viên', category = 'system' WHERE id = 'superadmin';
UPDATE cosa.roles SET name = 'Quản trị viên nền tảng', category = 'system' WHERE id = 'admin';
UPDATE cosa.roles SET name = 'Hỗ trợ viên', category = 'system' WHERE id = 'support';
UPDATE cosa.roles SET name = 'Sáng lập', category = 'leadership' WHERE id = 'founder';
UPDATE cosa.roles SET name = 'Đồng sáng lập', category = 'leadership' WHERE id = 'co-founder';
UPDATE cosa.roles SET name = 'Thành viên', category = 'community' WHERE id = 'user';

ALTER TABLE cosa.roles DROP COLUMN IF EXISTS scope;
ALTER TABLE cosa.roles DROP COLUMN IF EXISTS level;

-- Insert/Upsert 13 roles chuẩn của Cosa
INSERT INTO cosa.roles (id, name, category, description) VALUES
  ('superadmin', 'Quản trị viên', 'system',     'Quản trị tối cao toàn bộ nền tảng'),
  ('support',    'Hỗ trợ viên',   'system',     'Hỗ trợ khách hàng và vận hành hệ thống'),
  ('founder',    'Sáng lập',      'leadership', 'Nhà sáng lập doanh nghiệp / workspace'),
  ('co-founder', 'Đồng sáng lập', 'leadership', 'Đồng sáng lập doanh nghiệp / workspace'),
  ('mentor',     'Cố vấn',        'community',  'Cố vấn chuyên môn và phát triển doanh nghiệp'),
  ('investor',   'Nhà đầu tư',    'community',  'Nhà đầu tư / Quỹ đầu tư mạo hiểm'),
  ('tech',       'Công nghệ',     'department', 'Khối Kỹ thuật & Công nghệ'),
  ('marketing',  'Marketing',     'department', 'Khối Tiếp thị & Truyền thông'),
  ('sales',      'Kinh doanh',    'department', 'Khối Bán hàng & Phát triển thị trường'),
  ('finance',    'Tài chính',     'department', 'Khối Kế toán & Tài chính'),
  ('hr',         'Nhân sự',       'department', 'Khối Quản trị nhân sự'),
  ('operations', 'Vận hành',      'department', 'Khối Vận hành doanh nghiệp'),
  ('member',     'Thành viên',    'community',  'Thành viên chung')
ON CONFLICT (id) DO UPDATE 
SET name = EXCLUDED.name, category = EXCLUDED.category, description = EXCLUDED.description;

-- 2. Chuẩn hóa cosa.users: Bỏ cờ thừa is_platform_admin và platform_role_id
ALTER TABLE cosa.users DROP COLUMN IF EXISTS is_platform_admin CASCADE;
ALTER TABLE cosa.users DROP COLUMN IF EXISTS platform_role_id CASCADE;

-- 3. Chuẩn hóa cosa.profiles: id = users.id (PK & FK), thêm role_id
DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.columns 
    WHERE table_schema = 'cosa' AND table_name = 'profiles' AND column_name = 'user_id'
  ) THEN
    ALTER TABLE cosa.profiles RENAME COLUMN user_id TO id;
  END IF;
END $$;

ALTER TABLE cosa.profiles ADD COLUMN IF NOT EXISTS role_id TEXT REFERENCES cosa.roles(id);
ALTER TABLE cosa.profiles ADD COLUMN IF NOT EXISTS bio TEXT;
ALTER TABLE cosa.profiles ADD COLUMN IF NOT EXISTS headline TEXT;

-- 4. Bỏ tiền tố platform_ ở các bảng và cột liên quan đến Workspace
-- 4.1 Đổi tên bảng
ALTER TABLE IF EXISTS cosa.platform_workspaces RENAME TO workspaces;
ALTER TABLE IF EXISTS cosa.platform_workspace_memberships RENAME TO workspace_memberships;
ALTER TABLE IF EXISTS cosa.platform_workspace_sync_log RENAME TO workspace_sync_logs;

-- 4.2 Đổi tên cột trong cosa.workspaces
DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.columns 
    WHERE table_schema = 'cosa' AND table_name = 'workspaces' AND column_name = 'owner_user_id'
  ) THEN
    ALTER TABLE cosa.workspaces RENAME COLUMN owner_user_id TO owner_id;
  END IF;
END $$;

-- 4.3 Đổi tên cột trong cosa.workspace_memberships
DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.columns 
    WHERE table_schema = 'cosa' AND table_name = 'workspace_memberships' AND column_name = 'platform_workspace_id'
  ) THEN
    ALTER TABLE cosa.workspace_memberships RENAME COLUMN platform_workspace_id TO workspace_id;
  END IF;
END $$;

-- Đổi cột role thành role_id trỏ sang cosa.roles(id) trong workspace_memberships
DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.columns 
    WHERE table_schema = 'cosa' AND table_name = 'workspace_memberships' AND column_name = 'role'
  ) THEN
    ALTER TABLE cosa.workspace_memberships RENAME COLUMN role TO role_id;
  END IF;
END $$;

-- 4.4 Đổi tên cột trong cosa.workspace_sync_logs
DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.columns 
    WHERE table_schema = 'cosa' AND table_name = 'workspace_sync_logs' AND column_name = 'platform_workspace_id'
  ) THEN
    ALTER TABLE cosa.workspace_sync_logs RENAME COLUMN platform_workspace_id TO workspace_id;
  END IF;
END $$;

-- 4.5 Đổi tên cột trong cosa.workspace_licenses
DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.columns 
    WHERE table_schema = 'cosa' AND table_name = 'workspace_licenses' AND column_name = 'platform_workspace_id'
  ) THEN
    ALTER TABLE cosa.workspace_licenses RENAME COLUMN platform_workspace_id TO workspace_id;
  END IF;
END $$;

-- 4.6 Đổi tên cột trong cosa.workspace_entitlements
DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.columns 
    WHERE table_schema = 'cosa' AND table_name = 'workspace_entitlements' AND column_name = 'platform_workspace_id'
  ) THEN
    ALTER TABLE cosa.workspace_entitlements RENAME COLUMN platform_workspace_id TO workspace_id;
  END IF;
END $$;

-- 4.7 Đổi tên cột trong cosa.workspace_agent_policy
DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.columns 
    WHERE table_schema = 'cosa' AND table_name = 'workspace_agent_policy' AND column_name = 'platform_workspace_id'
  ) THEN
    ALTER TABLE cosa.workspace_agent_policy RENAME COLUMN platform_workspace_id TO workspace_id;
  END IF;
END $$;
