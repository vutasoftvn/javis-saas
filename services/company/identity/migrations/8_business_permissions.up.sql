-- Migration 8: Business permissions catalog, workspace roles, role permissions, scoped member role assignments, and workspace policy versions

CREATE TABLE IF NOT EXISTS core.permission_definitions (
  permission_key  TEXT PRIMARY KEY,
  domain          TEXT NOT NULL,
  description     TEXT,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Seed permission catalog
INSERT INTO core.permission_definitions (permission_key, domain, description) VALUES
  ('permissions.read', 'identity', 'Xem danh mục và phân quyền'),
  ('permissions.manage', 'identity', 'Cấu hình vai trò và gán quyền'),
  ('agent.policy.manage', 'agent', 'Quản lý chính sách và giới hạn của agent'),
  ('agent.sweep.manage', 'agent', 'Bật tắt và cấu hình task sweep của agent'),
  ('execution.plan.approve', 'operations', 'Duyệt execution plan thành task'),
  ('strategy.read', 'operations', 'Xem thông tin chiến lược và OKR'),
  ('strategy.write', 'operations', 'Tạo và cập nhật sáng kiến chiến lược'),
  ('strategy.target.manage', 'operations', 'Quản lý chỉ tiêu mục tiêu tuần và quý'),
  ('strategy.transition', 'operations', 'Chuyển đổi stage và trạng thái chiến lược'),
  ('finance.read', 'finance', 'Xem dữ liệu sổ sách tài chính'),
  ('finance.request.create', 'finance', 'Tạo đề nghị chi / thanh toán'),
  ('finance.request.approve', 'finance', 'Phê duyệt đề nghị chi / thanh toán'),
  ('finance.reconcile', 'finance', 'Đối soát giao dịch ngân hàng'),
  ('finance.period.close', 'finance', 'Đóng kỳ kế toán'),
  ('finance.report.read', 'finance', 'Xem báo cáo tài chính và snapshot'),
  ('legal.read', 'legal', 'Xem danh mục pháp lý và nghĩa vụ'),
  ('legal.obligation.manage', 'legal', 'Cập nhật và xử lý nghĩa vụ pháp lý'),
  ('ai.deployment.create', 'ai', 'Khởi tạo AI deployment'),
  ('ai.deployment.review', 'ai', 'Đánh giá rủi ro AI deployment'),
  ('ai.deployment.approve', 'ai', 'Phê duyệt kích hoạt AI deployment')
ON CONFLICT (permission_key) DO NOTHING;

CREATE TABLE IF NOT EXISTS core.workspace_roles (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id  BIGINT NOT NULL REFERENCES core.workspaces(id) ON DELETE CASCADE,
  role_key      TEXT NOT NULL,
  name          TEXT NOT NULL,
  is_system     BOOLEAN NOT NULL DEFAULT false,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT uq_workspace_roles_key UNIQUE (workspace_id, role_key)
);

CREATE TABLE IF NOT EXISTS core.role_permissions (
  role_id         UUID NOT NULL REFERENCES core.workspace_roles(id) ON DELETE CASCADE,
  permission_key  TEXT NOT NULL REFERENCES core.permission_definitions(permission_key) ON DELETE CASCADE,
  effect          TEXT NOT NULL CHECK (effect IN ('ALLOW', 'DENY', 'REQUIRE_APPROVAL')),
  conditions      JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  PRIMARY KEY (role_id, permission_key)
);

CREATE TABLE IF NOT EXISTS core.member_role_assignments (
  id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id          BIGINT NOT NULL REFERENCES core.workspaces(id) ON DELETE CASCADE,
  workforce_member_id   BIGINT NOT NULL REFERENCES core.workforce_members(id) ON DELETE CASCADE,
  role_id               UUID NOT NULL REFERENCES core.workspace_roles(id) ON DELETE CASCADE,
  project_id            BIGINT,
  legal_entity_id       BIGINT,
  valid_from            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  valid_until           TIMESTAMPTZ,
  created_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT check_valid_until_after_valid_from CHECK (valid_until IS NULL OR valid_until > valid_from)
);

CREATE INDEX IF NOT EXISTS idx_member_role_assignments_lookup
  ON core.member_role_assignments (workspace_id, workforce_member_id);

CREATE TABLE IF NOT EXISTS core.workspace_policy_versions (
  workspace_id      BIGINT NOT NULL REFERENCES core.workspaces(id) ON DELETE CASCADE,
  version           INTEGER NOT NULL,
  policy_hash       TEXT NOT NULL,
  actor_member_id   BIGINT,
  reason            TEXT,
  created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  PRIMARY KEY (workspace_id, version)
);
