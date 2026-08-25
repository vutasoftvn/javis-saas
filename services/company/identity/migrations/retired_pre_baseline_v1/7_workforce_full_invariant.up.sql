-- services/company/identity/migrations/7_workforce_full_invariant.up.sql

-- Constraint cũ (migration 6) chỉ chặn field đối nghịch, không bắt buộc field
-- đúng loại phải có mặt — một HUMAN không có human_user_id vẫn pass. Thay
-- bằng constraint đầy đủ 2 chiều theo DB_FINAL_CUTOVER.md §6.3.
ALTER TABLE core.workforce_members DROP CONSTRAINT workforce_members_type_consistency;

ALTER TABLE core.workforce_members ADD CONSTRAINT workforce_members_type_consistency CHECK (
  (member_type = 'HUMAN' AND human_user_id IS NOT NULL AND agent_spec_id IS NULL AND agent_spec_version IS NULL)
  OR
  (member_type = 'AI_AGENT' AND human_user_id IS NULL AND agent_spec_id IS NOT NULL AND agent_spec_version IS NOT NULL)
);
