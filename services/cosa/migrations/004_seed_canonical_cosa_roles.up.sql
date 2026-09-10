-- Fix a stale seed in 001_founder_trial_mvp_baseline: it seeds cosa.roles with
-- the pre-migration-27 set (scope/level columns, ids admin/user/auditor) and is
-- MISSING the `member` role.
--
-- services/cosa/services/auth.service.ts (registerPlatform inserts a profile
-- with role_id='member' for a no-workspace signup), company.service.ts and
-- workspace-invitation.service.ts all require `member` to exist. Without it,
-- POST /platform/auth/register fails the profiles_role_id_fkey constraint and
-- every cross-plane E2E dies at seed time.
--
-- Upsert the canonical role set from the deleted migration
-- 27_refactor_clean_roles_profiles_and_workspaces.up.sql. Idempotent; does NOT
-- delete the legacy user/auditor/admin rows (harmless extras — a fresh baseline
-- DB has no profile data referencing them, and dropping them risks an FK break
-- on a long-lived dev DB).

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
