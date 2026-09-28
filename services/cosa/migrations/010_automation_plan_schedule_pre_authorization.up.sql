-- 010_automation_plan_schedule_pre_authorization.up.sql
--
-- Plan hub vận hành đợt 2 B5 (Task 6, phần 1) — founder duyệt MỘT LẦN thẻ kế hoạch tự động hoá
-- (services/company `operating.automation_plan_proposals`, B4) rồi services/cosa tạo lịch có
-- snapshot uỷ quyền trước: capability nào được phép chạy KHÔNG hỏi lại founder mỗi lần
-- (`pre_authorized_capability_ids`, allowlist cứng ở workspace-schedule.service.ts), và danh
-- tính founder sở hữu lịch (`founder_member_id`/`founder_user_id`, người BẤM DUYỆT — xem
-- ADR-FOUNDER-CHANNEL-001 mục 5) để worker (Task 6b) mint company delegation đúng chủ.
-- `automation_plan_proposal_id` chỉ để truy vết + idempotency (không tạo lịch trùng khi retry
-- approve). `token_budget_per_run` snapshot ngân sách token/lần chạy đã duyệt.
--
-- Lịch cũ (tạo trước migration này, hoặc tạo qua route thủ công tab Lịch): mảng rỗng / NULL —
-- hành vi cũ không đổi (worker Task 6b coi rỗng = không có capability nào được pre-authorize).
-- Expand-only, idempotent.

ALTER TABLE control_plane.organization_schedule_definitions
  ADD COLUMN IF NOT EXISTS pre_authorized_capability_ids jsonb NOT NULL DEFAULT '[]'::jsonb,
  ADD COLUMN IF NOT EXISTS founder_member_id text,
  ADD COLUMN IF NOT EXISTS founder_user_id text,
  ADD COLUMN IF NOT EXISTS automation_plan_proposal_id text,
  ADD COLUMN IF NOT EXISTS token_budget_per_run integer;

ALTER TABLE control_plane.organization_schedule_executions
  ADD COLUMN IF NOT EXISTS pre_authorized_capability_ids_snapshot jsonb NOT NULL DEFAULT '[]'::jsonb,
  ADD COLUMN IF NOT EXISTS founder_member_id_snapshot text,
  ADD COLUMN IF NOT EXISTS founder_user_id_snapshot text,
  ADD COLUMN IF NOT EXISTS token_budget_per_run_snapshot integer;

CREATE INDEX IF NOT EXISTS idx_organization_schedule_definitions_proposal
  ON control_plane.organization_schedule_definitions (automation_plan_proposal_id)
  WHERE automation_plan_proposal_id IS NOT NULL;
