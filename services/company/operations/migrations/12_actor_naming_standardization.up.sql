-- services/company/operations/migrations/12_actor_naming_standardization.up.sql

-- Canonical actor = workforce_members.id (có thể là human hoặc AI agent),
-- không dùng user_id cho business actor. Chuẩn hoá tên cột về *_member_id.
-- tasks.assignee_id là cột chết (đã bị thay bởi assignee_member_id từ
-- trước, không còn service nào ghi vào nó) — xoá luôn, không rename.
ALTER TABLE operating.tasks DROP COLUMN IF EXISTS assignee_id;
ALTER TABLE strategy.initiatives RENAME COLUMN owner_id TO owner_member_id;
ALTER TABLE strategy.okr_objectives RENAME COLUMN owner_id TO owner_member_id;
ALTER TABLE strategy.projects RENAME COLUMN owner_id TO owner_member_id;
ALTER TABLE strategy.experiments RENAME COLUMN owner_workforce_member_id TO owner_member_id;
ALTER TABLE strategy.decision_records RENAME COLUMN actor_workforce_member_id TO actor_member_id;
