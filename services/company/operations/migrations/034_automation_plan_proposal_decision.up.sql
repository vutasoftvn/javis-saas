-- 034_automation_plan_proposal_decision.up.sql
--
-- Plan hub vận hành đợt 2 B5 (Task 6): ghi lại AI CHÍNH THỨC đã duyệt nháp kế hoạch tự động hoá
-- (`decided_by_member_id` / `decided_by_user_id`) — cần cho retry idempotent (gọi lại approve khi
-- đã APPROVED nhưng chưa link lịch phải trả lại đúng founder đã quyết định trước đó, không đọc lại
-- ctx của lần gọi lại vì có thể là request khác, dù cùng workspace).
-- "founder sở hữu lịch = người bấm duyệt" (ADR-FOUNDER-CHANNEL-001 mục 5) — không nhất thiết là
-- người đề xuất (`proposed_by_member_id`).
-- Expand-only, idempotent.

ALTER TABLE operating.automation_plan_proposals
  ADD COLUMN IF NOT EXISTS decided_by_member_id BIGINT REFERENCES core.workforce_members(id) ON DELETE SET NULL,
  ADD COLUMN IF NOT EXISTS decided_by_user_id TEXT;
