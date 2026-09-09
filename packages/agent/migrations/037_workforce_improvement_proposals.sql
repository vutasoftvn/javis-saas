-- Migration 037: Controlled improvement proposals (Task 7).
--
-- Evaluation Owner đề xuất cải tiến từ cohort/evidence; proposal KHÔNG tự
-- thay skill/model/quyền. Bất kỳ capability / autonomy / provider-model cost
-- limit / external write / workspace-wide rollout cần founder approval.
-- Canary tạo pinned revision MỚI chỉ cho attempt được chọn; run lịch sử
-- KHÔNG bị sửa attribution. Append-only proposal revision/events.
-- Expand-only + có down.

CREATE TABLE IF NOT EXISTS agent.workforce_improvement_proposals (
    proposal_id        UUID PRIMARY KEY,
    workspace_id       TEXT NOT NULL,
    agent_instance_id  UUID NOT NULL,
    created_by         TEXT NOT NULL,
    status             TEXT NOT NULL DEFAULT 'DRAFT'
                         CHECK (status IN (
                           'DRAFT','PENDING_FOUNDER_REVIEW','CANARY',
                           'APPROVED','REJECTED','ROLLED_BACK'
                         )),
    change_class       TEXT NOT NULL,   -- rubric | tag | sla | capability | autonomy | model_cost | external_write | rollout
    requires_founder   BOOLEAN NOT NULL DEFAULT true,
    baseline_evidence_refs JSONB NOT NULL DEFAULT '[]'::jsonb,
    hypothesis         TEXT NOT NULL,
    proposed_revision  JSONB NOT NULL DEFAULT '{}'::jsonb,
    candidate_definition_hash TEXT NULL,
    baseline_definition_hash  TEXT NULL,
    risk_cost_impact   JSONB NOT NULL DEFAULT '{}'::jsonb,
    canary_selection   JSONB NOT NULL DEFAULT '{}'::jsonb,
    rollback_plan      TEXT NULL,
    version            INTEGER NOT NULL DEFAULT 1,
    created_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at         TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_workforce_improvement_proposals_ws
    ON agent.workforce_improvement_proposals (workspace_id, agent_instance_id, status);

CREATE TABLE IF NOT EXISTS agent.workforce_improvement_events (
    event_id       UUID PRIMARY KEY,
    proposal_id    UUID NOT NULL REFERENCES agent.workforce_improvement_proposals(proposal_id) ON DELETE CASCADE,
    workspace_id   TEXT NOT NULL,
    event_type     TEXT NOT NULL,    -- created | submitted | canary_started | approved | rejected | rolled_back
    actor_id       TEXT NOT NULL,
    payload        JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);
