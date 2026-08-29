-- Migration: 014_promotion_evidence.sql
-- Description: Bảng agent_evals.promotion_evidence — bằng chứng bất biến
--   cho quyết định promotion, Wave M4. Khác 013 (ALTER bảng có sẵn), đây là
--   bảng MỚI vì chưa migration nào trước đó map được khái niệm này.
--
-- Ranh giới sở hữu: packages/agent/evals/ ghi bảng này (tạo evidence).
-- PromotionDecision/activation (quyền đổi trạng thái production) KHÔNG có
-- bảng tương ứng ở đây — thuộc services/cosa, xem
-- docs/implementation/M4_PROMOTION_CONTROL_PLANE_BOUNDARY.md.

CREATE TABLE IF NOT EXISTS agent_evals.promotion_evidence (
    evidence_id VARCHAR(64) PRIMARY KEY,
    target_kind VARCHAR(32) NOT NULL,
    target_id VARCHAR(128) NOT NULL,
    target_version VARCHAR(32) NOT NULL,
    target_definition_hash VARCHAR(64) NOT NULL,
    required_eval_run_ids JSONB NOT NULL DEFAULT '[]'::jsonb,
    observed_fingerprints JSONB NOT NULL DEFAULT '{}'::jsonb,
    policy_version VARCHAR(32) NOT NULL,
    policy_checks_passed BOOLEAN NOT NULL,
    check_details JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_promotion_evidence_target
    ON agent_evals.promotion_evidence(target_kind, target_id, target_version);
