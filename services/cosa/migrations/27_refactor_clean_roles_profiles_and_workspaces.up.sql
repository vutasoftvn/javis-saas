-- services/cosa/migrations/27_refactor_clean_roles_profiles_and_workspaces.up.sql

-- 1. Chuẩn hóa bảng cosa.roles: thêm name, category, sort_order, bỏ level, scope
ALTER TABLE cosa.roles ADD COLUMN IF NOT EXISTS name TEXT;
ALTER TABLE cosa.roles ADD COLUMN IF NOT EXISTS category TEXT;
ALTER TABLE cosa.roles ADD COLUMN IF NOT EXISTS sort_order INTEGER NOT NULL DEFAULT 0;

ALTER TABLE cosa.roles DROP COLUMN IF EXISTS scope;
ALTER TABLE cosa.roles DROP COLUMN IF EXISTS level;

-- Xóa bỏ các role rác cũ (user, auditor, admin...)
DELETE FROM cosa.roles 
WHERE id NOT IN (
  'superadmin', 'support', 'founder', 'co-founder', 'mentor', 'investor',
  'tech', 'marketing', 'sales', 'finance', 'hr', 'operations', 'member'
);

-- Insert/Upsert đúng chuẩn 13 roles của Cosa theo thứ tự hiển thị khoa học
INSERT INTO cosa.roles (id, name, category, sort_order, description) VALUES
  ('founder',    'Sáng lập',      'leadership', 1,  'Nhà sáng lập doanh nghiệp / workspace'),
  ('co-founder', 'Đồng sáng lập', 'leadership', 2,  'Đồng sáng lập doanh nghiệp / workspace'),
  ('mentor',     'Cố vấn',        'community',  3,  'Cố vấn chuyên môn và phát triển doanh nghiệp'),
  ('investor',   'Nhà đầu tư',    'community',  4,  'Nhà đầu tư / Quỹ đầu tư mạo hiểm'),
  ('tech',       'Công nghệ',     'department', 5,  'Khối Kỹ thuật & Công nghệ'),
  ('marketing',  'Marketing',     'department', 6,  'Khối Tiếp thị & Truyền thông'),
  ('sales',      'Kinh doanh',    'department', 7,  'Khối Bán hàng & Phát triển thị trường'),
  ('finance',    'Tài chính',     'department', 8,  'Khối Kế toán & Tài chính'),
  ('hr',         'Nhân sự',       'department', 9,  'Khối Quản trị nhân sự'),
  ('operations', 'Vận hành',      'department', 10, 'Khối Vận hành doanh nghiệp'),
  ('member',     'Thành viên',    'community',  11, 'Thành viên chung'),
  ('superadmin', 'Quản trị viên', 'system',     12, 'Quản trị tối cao toàn bộ nền tảng'),
  ('support',    'Hỗ trợ viên',   'system',     13, 'Hỗ trợ khách hàng và vận hành hệ thống')
ON CONFLICT (id) DO UPDATE 
SET name = EXCLUDED.name, 
    category = EXCLUDED.category, 
    sort_order = EXCLUDED.sort_order, 
    description = EXCLUDED.description;

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
