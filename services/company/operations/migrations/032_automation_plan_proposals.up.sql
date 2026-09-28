-- 032_automation_plan_proposals.up.sql
--
-- Plan hub vận hành đợt 2 B4: nháp kế hoạch tự động hoá do agent đề xuất qua capability
-- `automation.plan.propose` (T1 — nháp, không tác động ngoài). Bước gọi tool KHÔNG tạo lịch
-- thật; founder duyệt thẻ kế hoạch (B6) và B5 tạo lịch theo `id`, ghi `approved_schedule_id`.
-- Bảng cũng là nguồn đếm quota nháp/Project/ngày UTC (index (project_id, created_at)).
-- `plan` / `readiness` chỉ chứa dữ liệu đã chuẩn hoá ở service: nhãn kênh + trạng thái xác
-- minh, trạng thái connector — KHÔNG BAO GIỜ chat id, secret_ref hay token.
-- Expand-only, idempotent.

CREATE TABLE IF NOT EXISTS operating.automation_plan_proposals (
  id BIGINT PRIMARY KEY,
  workspace_id BIGINT NOT NULL,
  project_id BIGINT NOT NULL,
  proposed_by_member_id BIGINT NOT NULL,
  run_id TEXT,
  plan JSONB NOT NULL,
  readiness JSONB NOT NULL,
  status TEXT NOT NULL DEFAULT 'DRAFT',
  approved_schedule_id TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  decided_at TIMESTAMPTZ,
  CONSTRAINT fk_automation_plan_proposals_proj_ws FOREIGN KEY (project_id, workspace_id)
    REFERENCES strategy.projects(id, workspace_id) ON DELETE CASCADE,
  CONSTRAINT fk_automation_plan_proposals_member FOREIGN KEY (proposed_by_member_id)
    REFERENCES core.workforce_members(id) ON DELETE CASCADE,
  CONSTRAINT chk_automation_plan_proposals_status
    CHECK (status IN ('DRAFT', 'APPROVED', 'DISCARDED'))
);

CREATE INDEX IF NOT EXISTS idx_automation_plan_proposals_project_created
  ON operating.automation_plan_proposals (project_id, created_at);
