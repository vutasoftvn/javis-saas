# Integration: PydanticAI

## 1. Mục đích

`PydanticAIKernel` (`packages/agent_integrations/pydantic_ai/kernel.py`) — implementation `ExecutionKernel` dùng PydanticAI `Agent.run()` THẬT (package `pydantic-ai-slim>=1.0`), viết ở Wave 10 (2026-08-24) theo `COSA_AGENT_PLATFORM_BLUEPRINT_V2_RECONCILED_PLAN_2026-08-24.md` Phần 4.

## 2. Khi nào sử dụng

Chưa wire vào `apps/cosa/composition/agent_plane.py` — chỉ tồn tại như adapter tuỳ chọn đã pass conformance suite, chưa có consumer production nào. KHÔNG phải default (vẫn `OpenAIAgentsKernel` — manual loop, `packages/agent/kernel/`).

## 3. Điểm khác biệt kiến trúc so với `LangChainKernel`/`RealOpenAIAgentsSDKKernel`

Approval-gate dùng cơ chế **"deferred tools" NATIVE của PydanticAI**
(`Tool(fn, requires_approval=True)` → model gọi tool này → `Agent.run()` trả
`DeferredToolRequests` thay vì raise/pause thủ công → resume bằng
`DeferredToolRequests.build_results(approvals={call_id: True/False})` +
`Agent.run(message_history=..., deferred_tool_results=...)`), thay vì tự cài
policy evaluator can thiệp giữa vòng lặp reasoning như 2 kernel kia —
PydanticAI đã có sẵn khái niệm này ở tầng framework.

Checkpoint dùng `result.all_messages_json()` + `ModelMessagesTypeAdapter` —
cơ chế serialize message history gốc của PydanticAI, không tự viết
serializer riêng. `DeferredToolRequests` (dataclass, không phải Pydantic
model — không có `.model_dump()`) cần serialize thủ công (`_deferred_requests_to_dict`/`_deferred_requests_from_dict` trong `kernel.py`) để lưu vào checkpoint cùng message history.

## 4. Test conformance

`packages/agent_testkit/kernel_conformance/test_pydantic_ai_kernel.py` — 5 test cùng shape với LangChain/OpenAI Agents SDK (basic response, provider failure typed, tool call exact identity, approval pause/resume, cancellation), dùng `FunctionModel` (fixture chính thức của PydanticAI cho test, không cần API key thật). Cả 5 pass ngay lần viết đầu — API `DeferredToolRequests`/`build_results()` khớp đúng mental model dự kiến, không phát hiện bug nào trong lúc viết (khác 2 kernel kia, mỗi kernel đều lộ ≥1 bug thật khi chạy lần đầu).

## 5. Việc CHƯA làm

- Chưa test với DeepSeek/model provider thật (chỉ `FunctionModel` fake) — PydanticAI hỗ trợ provider OpenAI-compatible qua `OpenAIModel(..., base_url=...)`, khả thi nhưng chưa làm trong phiên này (đã ưu tiên làm live test cho OpenAI Agents SDK thay vì lặp lại cho cả 3 kernel).
- Chưa pass đủ điều kiện production (review ADR-RUNTIME-001, benchmark, v.v. — giống mọi adapter tuỳ chọn khác).
