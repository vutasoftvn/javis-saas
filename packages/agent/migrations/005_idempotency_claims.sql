-- Migration: 005_idempotency_claims.sql
-- Description: Atomic idempotency claim table — thay thế check-then-act không
-- atomic hiện tại ở CapabilityGateway (Bước 5: get_tool_call_by_idempotency rồi
-- mới save_tool_call, có window race giữa 2 worker). Theo Blueprint V2 §20 và
-- COSA_AGENT_PLATFORM_BLUEPRINT_V2_RECONCILED_PLAN_2026-08-24.md Phần D.
--
-- Ghi chú phạm vi: Blueprint V2 gốc gộp bảng này cùng run_runtime_bindings,
-- runtime_checkpoints, run_model_calls vào 1 migration 005 duy nhất. Migration
-- này CHỈ tạo idempotency_claims — 3 bảng còn lại phục vụ multi-runtime adapter
-- (LangChain/LangGraph, Wave 4) chưa có consumer nào trong code hiện tại, tạo
-- trước sẽ là bảng rỗng không ai ghi (vi phạm CLAUDE.md "không tạo feature khi
-- chưa cần"). Sẽ tạo trong migration riêng ở đầu Wave 4 khi thực sự cần.

CREATE TABLE IF NOT EXISTS agent.idempotency_claims (
    claim_id VARCHAR(64) PRIMARY KEY,
    tenant_id VARCHAR(64),
    capability_id VARCHAR(128) NOT NULL,
    scope_kind VARCHAR(32) NOT NULL DEFAULT 'RUN',
    scope_key VARCHAR(128) NOT NULL,
    idempotency_key VARCHAR(128) NOT NULL,
    payload_hash VARCHAR(64) NOT NULL,
    run_id VARCHAR(64) NOT NULL REFERENCES agent.runs(run_id) ON DELETE CASCADE,
    tool_call_id VARCHAR(128) NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'running',
    result_hash VARCHAR(64),
    result_payload JSONB,
    error_message TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_agent_idempotency_claims_scope
        UNIQUE (scope_kind, scope_key, capability_id, idempotency_key)
);

CREATE INDEX IF NOT EXISTS idx_agent_idempotency_claims_run ON agent.idempotency_claims(run_id);
CREATE INDEX IF NOT EXISTS idx_agent_idempotency_claims_status ON agent.idempotency_claims(status);
