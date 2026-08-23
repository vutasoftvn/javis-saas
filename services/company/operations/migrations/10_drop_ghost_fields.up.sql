-- services/company/operations/migrations/10_drop_ghost_fields.up.sql

-- brain_id/mvp_stage_id/offering_id là ghost field: không có bảng owner
-- (knowledge.brains, commercial.offerings không tồn tại), chỉ được set/đọc
-- xuyên suốt như DTO pass-through, không dùng trong bất kỳ query/filter nào.
-- Xem docs/superpowers/specs/2026-08-23-identity-foundation-plan-a-design.md
-- mục "Plan B" điểm 2.
ALTER TABLE strategy.initiatives DROP COLUMN IF EXISTS brain_id;
ALTER TABLE strategy.initiatives DROP COLUMN IF EXISTS offering_id;
ALTER TABLE strategy.okr_cycles DROP COLUMN IF EXISTS brain_id;
ALTER TABLE strategy.okr_cycles DROP COLUMN IF EXISTS mvp_stage_id;
ALTER TABLE operating.twelve_week_cycles DROP COLUMN IF EXISTS brain_id;
ALTER TABLE strategy.portfolios DROP COLUMN IF EXISTS brain_id;
ALTER TABLE strategy.projects DROP COLUMN IF EXISTS brain_id;
