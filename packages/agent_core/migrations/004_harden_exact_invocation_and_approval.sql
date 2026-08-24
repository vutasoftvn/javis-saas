-- Migration: 004_harden_exact_invocation_and_approval.sql
-- Description: Harden exact invocation identity (run_id, tool_call_id) trên
-- agent_core.run_tool_calls + thêm CAS field cho agent_core.approvals.
-- Theo COSA_AGENT_PLATFORM_BLUEPRINT_V2_RECONCILED_PLAN_2026-08-24.md Phần C.2.
--
-- Ghi chú phạm vi: đổi PRIMARY KEY sang composite (run_id, tool_call_id), NHƯNG
-- vẫn giữ UNIQUE(tool_call_id) — tool_call_id hiện được sinh bằng uuid4 (globally
-- unique trên thực tế), nên các call site đang gọi get_tool_call(tool_call_id)
-- (packages/agent_core/capabilities/gateway.py, approval_service.py) tiếp tục
-- đúng mà không cần đổi signature Protocol trong migration này. Đổi Protocol
-- get_tool_call() sang nhận cả run_id là việc hardening sâu hơn, để lại cho một
-- migration sau nếu cần — không bundle vào đây để giữ thay đổi nhỏ nhất an toàn.

-- 1. Đổi PRIMARY KEY của agent_core.run_tool_calls sang composite (run_id, tool_call_id)
ALTER TABLE agent_core.run_tool_calls DROP CONSTRAINT run_tool_calls_pkey;
ALTER TABLE agent_core.run_tool_calls ADD CONSTRAINT run_tool_calls_pkey PRIMARY KEY (run_id, tool_call_id);
ALTER TABLE agent_core.run_tool_calls ADD CONSTRAINT uq_agent_core_run_tool_calls_tool_call_id UNIQUE (tool_call_id);

-- 2. Đổi FK của agent_core.approvals sang composite (run_id, tool_call_id)
ALTER TABLE agent_core.approvals DROP CONSTRAINT approvals_tool_call_id_fkey;
ALTER TABLE agent_core.approvals
    ADD CONSTRAINT approvals_run_tool_call_fkey
    FOREIGN KEY (run_id, tool_call_id)
    REFERENCES agent_core.run_tool_calls(run_id, tool_call_id)
    ON DELETE CASCADE;

-- 3. CAS field cho quyết định approval (Blueprint V2 §21) — atomic decision:
--    UPDATE ... SET status=:decision, decision_version = decision_version + 1
--    WHERE approval_id=:id AND status='pending' AND decision_version=:expected
--    RETURNING *;  (wiring vào approval_service.py là việc của Wave 2)
ALTER TABLE agent_core.approvals ADD COLUMN IF NOT EXISTS decision_version INTEGER NOT NULL DEFAULT 0;
