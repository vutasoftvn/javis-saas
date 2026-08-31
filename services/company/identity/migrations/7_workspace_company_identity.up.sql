-- services/company/identity/migrations/7_workspace_company_identity.up.sql
-- Founder phải thiết lập Vision/Mission/Core Values cho workspace — chặn
-- cứng Hub tới khi điền (frontend gate, xem HubAuthMixin.ensureAuthenticated).
-- Quan hệ 1-1 với workspace, không cần bảng con.
ALTER TABLE core.workspaces
  ADD COLUMN vision TEXT,
  ADD COLUMN mission TEXT,
  ADD COLUMN core_values TEXT;
