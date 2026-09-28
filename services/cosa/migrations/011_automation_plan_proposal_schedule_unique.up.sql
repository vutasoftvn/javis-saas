-- 011_automation_plan_proposal_schedule_unique.up.sql
--
-- Fix review "Needs fixes" Critical 2 (Task 6, B5 phần 1) — migration 010 chỉ có INDEX thường
-- trên `automation_plan_proposal_id`, không chặn được 2 request approve chạy đồng thời cho ĐÚNG
-- 1 proposal cùng tạo 2 lịch (check-then-create ở `automation-plan-approval.service.ts` không có
-- lock/transaction bọc quanh gọi HTTP sang services/company). Company `FOR UPDATE` chỉ serialize
-- DRAFT -> APPROVED, KHÔNG chặn 2 lần gọi `createWorkspaceSchedule` phía services/cosa nếu cả 2
-- request đều thấy proposal đã APPROVED (vd. lần đầu approve rồi retry trong lúc lịch đầu chưa kịp
-- ghi xong, hoặc 2 tab).
--
-- UNIQUE INDEX (partial, chỉ áp cho giá trị NOT NULL — lịch cũ/tạo tay có `automation_plan_
-- proposal_id IS NULL` không bị ảnh hưởng) khiến request thua chạy INSERT thứ 2 nhận lỗi
-- unique_violation (23505) ở tầng DB — `approveAutomationPlan` bắt lỗi này và coi như idempotency
-- path (đọc lại lịch đã có bằng `findScheduleDefinitionByProposalId`, không tạo lịch thứ hai).
-- Thay luôn INDEX thường của 010 (`idx_organization_schedule_definitions_proposal`) bằng UNIQUE
-- INDEX cùng điều kiện — tránh 2 index trùng cột, và INDEX cũ không phục vụ mục đích gì nếu đã có
-- UNIQUE INDEX (Postgres dùng UNIQUE INDEX cho cả lookup thường).
-- Expand-only, idempotent.

DROP INDEX IF EXISTS control_plane.idx_organization_schedule_definitions_proposal;

CREATE UNIQUE INDEX IF NOT EXISTS uq_organization_schedule_definitions_proposal
  ON control_plane.organization_schedule_definitions (automation_plan_proposal_id)
  WHERE automation_plan_proposal_id IS NOT NULL;
