-- services/cosa/migrations/27_refactor_clean_roles_profiles_and_workspaces.up.sql

-- 1. Chuẩn hóa cosa.roles: Thêm name, category, sort_order, nới lỏng legacy NOT NULL constraints và upsert 13 roles
ALTER TABLE cosa.roles ADD COLUMN IF NOT EXISTS name TEXT NOT NULL DEFAULT 'Legacy role';
ALTER TABLE cosa.roles ADD COLUMN IF NOT EXISTS category TEXT NOT NULL DEFAULT 'legacy';
ALTER TABLE cosa.roles ADD COLUMN IF NOT EXISTS sort_order INTEGER NOT NULL DEFAULT 0;

ALTER TABLE cosa.roles ALTER COLUMN scope DROP NOT NULL;
ALTER TABLE cosa.roles ALTER COLUMN level DROP NOT NULL;

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

-- 2. Thêm các trường profile mới cho cosa.profiles
ALTER TABLE cosa.profiles
  ADD COLUMN IF NOT EXISTS role_id TEXT NOT NULL DEFAULT 'member'
  REFERENCES cosa.roles(id);
ALTER TABLE cosa.profiles ADD COLUMN IF NOT EXISTS bio TEXT;
ALTER TABLE cosa.profiles ADD COLUMN IF NOT EXISTS headline TEXT;
