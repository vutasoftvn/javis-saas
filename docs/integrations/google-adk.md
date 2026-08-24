# Integration: Google ADK

## Trạng thái: SHIPPED production, nhưng NGOÀI `packages/agent_integrations/`

Khác mọi integration khác trong thư mục này, Google ADK đã **chạy production thật** — `AdkCofounderWorkflow` ở `legacy/agent_runtime/workforce/agents/orchestration/adk/` (xác nhận lại đường dẫn 2026-08-24 — `legacy/backend/app/workforce/...` không tồn tại, là suy đoán sai của phiên trước), dùng `google-adk==2.7.0`, có `CosaGovernedTool` (wrap tool qua governance audit) và `CosaModelGatewayLlm` (LiteLLM invoker, circuit breaker, fallback). Xem `docs/agent-platform/ADK_INTEGRATION.md` cho chi tiết đầy đủ (tài liệu có từ trước phiên này).

## Chưa migrate vào `packages/agent_integrations/google_adk/`

Đây là việc tồn đọng thật — kiến trúc target (`ADR-RUNTIME-ADAPTERS.md`) muốn MỌI runtime adapter nằm trong `packages/agent_integrations/`, nhưng ADK production hiện tại nằm ở `legacy/backend/` (ngoài biên giới `packages/`). Migrate là 1 việc lớn riêng (cần port `CosaGovernedTool`/`CosaModelGatewayLlm` sang implement contract `agent_core.contracts.*` mới, không phục hồi business object cũ nguyên trạng — theo đúng Blueprint V2 §6.3), **chưa làm trong phiên Wave 0-11**.

## Không migrate không có nghĩa là kém quan trọng

`google-adk` xác nhận import được trong môi trường phát triển 2026-08-24 (Python 3.9, dù có warning "non-supported Python version"). ADK vẫn là integration TRƯỞNG THÀNH NHẤT hiện có trong toàn hệ thống — quan trọng hơn LangChain (mới, 0 dòng code trước Wave 4) về mặt production-readiness, dù không nằm trong biên giới package target.

## Cập nhật 2026-08-24: adapter GENERIC mới, KHÔNG phải migrate `AdkCofounderWorkflow`

`packages/agent_integrations/google_adk/kernel.py` (class `GoogleAdkKernel`) —
implement `ExecutionKernel` Protocol dùng `google.adk.runners.Runner`/
`google.adk.agents.LlmAgent` GENERIC (không phải wrap/di chuyển
`AdkCofounderWorkflow` — đó vẫn là business pipeline production cụ thể domain
"cofounder mission", nằm nguyên ở
`legacy/agent_runtime/workforce/agents/orchestration/adk/workflow.py`,
KHÔNG migrate — xem mục "Chưa migrate" ở trên, vẫn đúng, chưa thay đổi).

**Phạm vi cố ý thu hẹp:** chỉ implement `run()` (basic response + tool call
ALLOW-path) — 3 test conformance pass
(`packages/agent_testkit/kernel_conformance/test_adk_kernel.py`).
`resume()`/`cancel()` raise `NotImplementedError` tường minh (có test xác
nhận), KHÔNG giả vờ hỗ trợ — ADK dùng session-based state
(`InMemorySessionService`/event streaming qua `Runner.run_async()`) khác hẳn
mô hình checkpoint đơn giản của OpenAI Agents SDK/PydanticAI, cần nghiên cứu
sâu hơn `resumability_config`/`FunctionTool(require_confirmation=...)` +
`tool_context.request_confirmation()` trước khi implement approval-pause/
resume đúng — để lại cho lần hardening sau khi có nhu cầu thật.

## Việc cần làm khi migrate

1. Đọc kỹ `legacy/agent_runtime/workforce/agents/orchestration/adk/` + `docs/agent-platform/ADK_INTEGRATION.md`.
2. Thiết kế `ADKKernel` implement `agent_core.contracts.kernel.ExecutionKernel` (giống `LangChainKernel`/`OpenAIAgentsKernel`).
3. Port `CosaGovernedTool` → gọi `CapabilityGateway.execute()` (không tự implement governance riêng).
4. Port `CosaModelGatewayLlm` → có thể tái dùng `LiteLLMModelClient` đã có (Wave 4) thay vì viết lại circuit breaker.
5. Chạy conformance suite (`packages/agent_testkit/kernel_conformance/`) trước khi coi migration hoàn tất.
