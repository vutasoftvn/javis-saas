-- 002_seed_permission_definitions.up.sql
--
-- Startup Core Task-2 reconciliation: the clean-slate 001 identity baseline
-- creates core.permission_definitions but seeds zero rows, while
-- core.role_permissions.permission_key has a FK to it. Any role/permission
-- assignment (production onboarding + tests) fails without the catalog.
-- Seeds the 26 keys from identity/services/permission-catalog.ts
-- (PERMISSION_CATALOG). Idempotent via ON CONFLICT.

INSERT INTO core.permission_definitions (permission_key, domain, description) VALUES
  ('permissions.read',            'identity',   'Xem danh mục và phân quyền'),
  ('permissions.manage',          'identity',   'Cấu hình vai trò và gán quyền'),
  ('agent.policy.manage',         'agent',      'Quản lý chính sách và giới hạn của agent'),
  ('agent.sweep.manage',          'agent',      'Bật tắt và cấu hình task sweep của agent'),
  ('execution.plan.approve',      'operations', 'Duyệt execution plan thành task'),
  ('strategy.read',               'operations', 'Xem thông tin chiến lược và OKR'),
  ('strategy.write',              'operations', 'Tạo và cập nhật sáng kiến chiến lược'),
  ('strategy.target.manage',      'operations', 'Quản lý chỉ tiêu mục tiêu tuần và quý'),
  ('strategy.transition',         'operations', 'Chuyển đổi stage và trạng thái chiến lược'),
  ('strategy.framework.manage',   'operations', 'Cấu hình khung chiến lược và policy workspace'),
  ('strategy.okr.publish',        'operations', 'Công bố mục tiêu chiến lược và OKRs'),
  ('strategy.initiative.approve', 'operations', 'Phê duyệt sáng kiến chiến lược'),
  ('strategy.review.close',       'operations', 'Chốt đánh giá chu kỳ và review chiến lược'),
  ('strategy.agent.configure',    'operations', 'Cấu hình và phân quyền agent chiến lược'),
  ('finance.read',                'finance',    'Xem dữ liệu sổ sách tài chính'),
  ('finance.transaction.record',  'finance',    'Ghi nhận giao dịch tài chính (thu/chi) vào sổ sách'),
  ('finance.request.create',      'finance',    'Tạo đề nghị chi / thanh toán'),
  ('finance.request.approve',     'finance',    'Phê duyệt đề nghị chi / thanh toán'),
  ('finance.reconcile',           'finance',    'Đối soát giao dịch ngân hàng'),
  ('finance.period.close',        'finance',    'Đóng kỳ kế toán'),
  ('finance.report.read',         'finance',    'Xem báo cáo tài chính và snapshot'),
  ('legal.read',                  'legal',      'Xem danh mục pháp lý và nghĩa vụ'),
  ('legal.obligation.manage',     'legal',      'Cập nhật và xử lý nghĩa vụ pháp lý'),
  ('ai.deployment.create',        'ai',         'Khởi tạo AI deployment'),
  ('ai.deployment.review',        'ai',         'Đánh giá rủi ro AI deployment'),
  ('ai.deployment.approve',       'ai',         'Phê duyệt kích hoạt AI deployment')
ON CONFLICT (permission_key) DO NOTHING;
