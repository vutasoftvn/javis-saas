-- Migration: 013_eval_suite_run_fingerprints.sql
-- Description: Mở rộng agent_evals.suites/runs/skill_mutations (migration
--   008) để hỗ trợ EvalSuite version+fingerprint, EvalRun suite_ref
--   fingerprint, và Skill Optimization Lab eval_run_id lineage —
--   Wave M3 (ADR-ARTIFACT-IDENTITY-001, docs/implementation/
--   marin-patterns-adjusted-plan.md).
--
-- 008_agent_evals.sql đã apply là bất biến — không sửa file đó, ALTER bằng
-- migration mới này thay vào đó.

ALTER TABLE agent_evals.suites
    ADD COLUMN IF NOT EXISTS version VARCHAR(32) NOT NULL DEFAULT '1.0.0';

ALTER TABLE agent_evals.suites
    ADD COLUMN IF NOT EXISTS definition_hash VARCHAR(64);

-- `suites` hiện chỉ có suite_id/name/target_kind/target_id/description —
-- KHÔNG đủ để tái tạo đầy đủ EvalSuite (thiếu case_ids/scorer_version/
-- pass_thresholds/metadata). Thêm content JSONB để lưu snapshot đầy đủ tại
-- thời điểm publish — cùng pattern agent_registry.published_specs.content
-- (migration 007) đã dùng cho AgentSpec/PromptSpec/ModelPolicySpec.
ALTER TABLE agent_evals.suites
    ADD COLUMN IF NOT EXISTS content JSONB;

ALTER TABLE agent_evals.runs
    ADD COLUMN IF NOT EXISTS suite_version VARCHAR(32);

ALTER TABLE agent_evals.runs
    ADD COLUMN IF NOT EXISTS suite_definition_hash VARCHAR(64);

-- `runs.suite_id` hiện là NOT NULL FK bắt buộc trỏ tới agent_evals.suites —
-- xung đột với EvalRun.suite_ref là Optional (Task 3): Skill Optimization
-- Lab tạo EvalRun ad-hoc (suite_ref=None, không gắn EvalSuite đã publish).
-- Bỏ NOT NULL + bỏ FK — sau thay đổi này, `suite_id` trở thành cột mô tả
-- thuần (lưu suite logical id khi có), CÙNG kiểu với `target_kind`/
-- `target_id`/`target_version`/`target_definition_hash` ở 4 dòng trên vốn
-- cũng KHÔNG có FK — nhất quán trong cùng bảng, exact identity đã được đảm
-- bảo qua `suite_version`+`suite_definition_hash` (2 cột mới ở trên), không
-- cần FK để xác thực. Tên constraint chuẩn Postgres cho REFERENCES khai báo
-- inline là `<table>_<column>_fkey` — dùng `IF EXISTS` nên an toàn dù tên
-- thật khác (không lỗi nếu constraint không tồn tại với tên đó).
ALTER TABLE agent_evals.runs
    DROP CONSTRAINT IF EXISTS runs_suite_id_fkey;

ALTER TABLE agent_evals.runs
    ALTER COLUMN suite_id DROP NOT NULL;

-- Wire Skill Optimization Lab eval evidence lineage — SkillMutationRecord
-- (packages/agent_core/skills/lab/models.py) giờ có thể tham chiếu đúng
-- EvalRun đã tạo cho round mutation đó (Wave M3 Task 6).
ALTER TABLE agent_evals.skill_mutations
    ADD COLUMN IF NOT EXISTS eval_run_id VARCHAR(64);
