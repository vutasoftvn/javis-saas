-- Migration 34: Workspace invitations (ADR-WORKSPACE-INVITATION-001)
--
-- Thay thế luồng self-join bằng company_id trần bằng invitation có hạn, có
-- người cấp quyền và audit được. Token thô KHÔNG bao giờ được lưu — chỉ lưu
-- SHA-256 hash (`token_hash`). Xem ADR-WORKSPACE-INVITATION-001 cho đầy đủ
-- quyết định (role giới hạn member/admin, expiry mặc định 168h, single-use,
-- idempotent retry-after-accept).

CREATE TABLE IF NOT EXISTS cosa.workspace_invitations (
  id                  BIGINT NOT NULL PRIMARY KEY,
  workspace_id        BIGINT NOT NULL REFERENCES cosa.workspaces(id) ON DELETE CASCADE,
  email_normalized    TEXT NOT NULL,
  role_id             TEXT NOT NULL REFERENCES cosa.roles(id) CHECK (role_id IN ('member', 'admin')),
  token_hash          TEXT NOT NULL,
  status              TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'accepted', 'revoked', 'expired')),
  invited_by_user_id  BIGINT NOT NULL REFERENCES cosa.users(id) ON DELETE CASCADE,
  expires_at          TIMESTAMPTZ NOT NULL,
  accepted_at         TIMESTAMPTZ,
  revoked_at          TIMESTAMPTZ,
  created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Chỉ 1 lời mời "pending" cho cùng (workspace, email) tại một thời điểm —
-- tránh chồng lấn nhiều token hợp lệ cho cùng một email.
CREATE UNIQUE INDEX IF NOT EXISTS ux_workspace_invitations_pending_email
  ON cosa.workspace_invitations (workspace_id, email_normalized)
  WHERE status = 'pending';

-- Tra cứu accept theo hash phải nhanh và duy nhất.
CREATE UNIQUE INDEX IF NOT EXISTS ux_workspace_invitations_token_hash
  ON cosa.workspace_invitations (token_hash);

CREATE INDEX IF NOT EXISTS idx_workspace_invitations_workspace
  ON cosa.workspace_invitations (workspace_id);

-- `cosa.workspace_memberships.role` (migration 18, tên gốc
-- `platform_workspace_memberships`) vẫn còn CHECK cũ chỉ cho phép
-- ('founder','member','viewer') — không cho phép 'admin'. Nhưng
-- `workspace-settings.service.ts::WORKSPACE_OPERATOR_ROLES` và
-- `workspace-connector.handler.ts::CONNECTOR_MANAGE_OTHERS_ROLES` đã coi
-- 'co-founder' và 'admin' là role hợp lệ của một membership từ trước — CHECK
-- cũ đã lỗi thời so với phần còn lại của codebase. ADR-WORKSPACE-INVITATION-001
-- cấp invitation role 'admin' nên constraint phải được nới để chấp nhận giá
-- trị này (Expand — chỉ mở rộng tập giá trị cho phép, không xoá giá trị cũ).
ALTER TABLE cosa.workspace_memberships
  DROP CONSTRAINT IF EXISTS platform_workspace_memberships_role_check;
ALTER TABLE cosa.workspace_memberships
  ADD CONSTRAINT workspace_memberships_role_check
  CHECK (role IN ('founder', 'co-founder', 'admin', 'member', 'viewer'));
