# ADR-DURABLE-IDENTITY: `(run_id, tool_call_id)` là identity bất biến xuyên suốt kernel → gateway → registry

- **Trạng thái:** ACCEPTED — hardened qua Wave 1-4 (2026-08-24)
- **Ngày quyết định:** 2026-08-24
- **Tác giả:** COSA Core Architecture Team
- **Tham chiếu:**
  - `COSA_AGENT_PLATFORM_IMPLEMENTATION_BLUEPRINT_V2_2026-08-24.md` §8, §16-21
  - `COSA_AGENT_PLATFORM_BLUEPRINT_V2_RECONCILED_PLAN_2026-08-24.md` Phần C.2, D, Phần F

---

## 1. Bối cảnh

Invariant cốt lõi của Agent Platform (Blueprint V2 §8.2): `InvocationIdentity before approval == after resume == at side effect`. Trước Wave 1, `agent_core.run_tool_calls.tool_call_id` là PK độc lập (không composite với `run_id`), và audit Wave 4 phát hiện `OpenAIAgentsKernel._execute_tool()` từng TỰ SINH `run_id`/`tool_call_id` mới trong 1 nhánh fallback — vi phạm trực tiếp invariant này.

## 2. Quyết định

1. **`agent_core.run_tool_calls` PK composite `(run_id, tool_call_id)`** (migration 004) — giữ thêm `UNIQUE(tool_call_id)` để không phải đổi signature `get_tool_call(tool_call_id)` ở các call site hiện tại (quyết định thu hẹp phạm vi có ghi chú trong chính migration).
2. **`agent_core.approvals` FK composite** tới `run_tool_calls(run_id, tool_call_id)` — approval luôn bind đúng 1 invocation cụ thể, không lookup theo tên action.
3. **CAS (Compare-And-Swap) cho quyết định approval** (`decision_version` column, migration 004) — `decide_approval()` chỉ thành công nếu `status='pending'`, tránh 2 request cùng quyết định 1 approval âm thầm ghi đè nhau.
4. **Kernel/Gateway KHÔNG BAO GIỜ tự sinh lại `tool_call_id`/`run_id`** một khi đã có — đây là quy tắc code-level bắt buộc, không chỉ nguyên tắc trừu tượng. Bug thật đã tìm thấy và sửa: `_execute_tool()` (cả `OpenAIAgentsKernel` và `LangChainKernel`) nhận `run_id`/`tool_call_id` tường minh từ call site, không tự `uuid.uuid4()` mới trong nhánh fallback `GatewayExecutionRequest`.
5. **Atomic idempotency claim** (`agent_core.idempotency_claims`, migration 005) thay thế check-then-act không atomic — `INSERT ... ON CONFLICT DO NOTHING`. Phân biệt rõ "cùng invocation tiếp tục" (cho phép, vd resume sau approval) vs "invocation khác đua giành" (chặn, trả `in_progress`) dựa vào so khớp `(run_id, tool_call_id)` của claim.
6. **Governance accumulator durable, không in-memory riêng của Gateway** (`GovernanceStateStore`, sửa sau khi hoàn thành Wave 0-11) — cùng invariant monotonic-across-restart.

## 3. Test chứng minh (không chỉ tuyên bố)

- `test_kernel_allow_path_tool_execution_preserves_real_run_and_tool_call_id` — chứng minh bug đã sửa.
- `test_concurrent_gateway_execute_same_idempotency_key_only_one_side_effect` — 2 request độc lập, `asyncio.gather`, handler có yield point thật, chỉ 1 side effect.
- `test_decide_approval_is_atomic_cas_exactly_one_decision_wins` — CAS approval.
- `test_governance_accumulator_survives_gateway_restart` — Gateway instance mới hoàn toàn (mô phỏng restart), governance_store durable giữ đúng state.

## 4. Hệ quả & rủi ro còn lại

- **Migration 004/005 CHƯA chạy trên Postgres thật** trong môi trường phát triển phiên này (không có Postgres) — cần chạy trên staging trước khi tin tưởng cho production.
- **`get_tool_call(tool_call_id)` vẫn nhận 1 tham số** (không phải `(run_id, tool_call_id)` đầy đủ) — an toàn nhờ `UNIQUE(tool_call_id)` nhưng chưa hardening triệt để theo đúng tinh thần composite key; để lại cho 1 pass sâu hơn nếu cần.
