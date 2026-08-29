# Hướng dẫn: Thêm runtime/kernel mới

## Khi nào cần

Khi muốn thêm 1 execution engine mới (vd PydanticAI, CrewAI) implement contract `ExecutionKernel` — KHÔNG phải khi chỉ cần đổi model provider (xem `add-capability.md`/`docs/integrations/litellm.md` cho việc đó).

## Vị trí code

`packages/agent_integrations/<runtime-name>/kernel.py` — KHÔNG đặt trong `packages/agent/kernel/` (chỉ `OpenAIAgentsKernel` hiện tại ở đó do lịch sử; runtime mới đi vào `agent_integrations` theo `ADR-RUNTIME-ADAPTERS.md`).

## Các bước

1. Đọc `packages/agent/contracts/kernel.py` — implement đúng Protocol `ExecutionKernel` (`run`, `resume`, `cancel`, `stream`).
2. **Không tự sinh `(run_id, tool_call_id)`** — đây là bug thật đã tìm thấy và fix ở `OpenAIAgentsKernel._execute_tool()` trong phiên này (generate random ID trong fallback branch → FK violation với Postgres thật). Mọi tool invocation phải nhận `run_id`/`tool_call_id` từ caller, không tự tạo.
3. Mọi side effect PHẢI đi qua `CapabilityGateway.execute()` — kernel không tự gọi external API/DB trực tiếp cho tool.
4. Model call lỗi → raise `AgentRuntimeError` (`packages/agent/contracts/errors.py`), KHÔNG convert thành assistant text thành công (anti-pattern đã fix ở `_call_model()`).
5. Dùng `PromptBundle` (`packages/agent/prompts/bundle.py`) để render system message — không tự ghép `spec.instructions` trần.
6. Viết `packages/agent_testkit/kernel_conformance/test_<runtime>_kernel.py` — bắt buộc pass trước khi coi kernel "sẵn sàng candidate" (theo đúng process đã áp dụng cho `LangChainKernel`).
7. Đăng ký trong `apps/cosa/composition/agent_plane.py` qua nhánh `runtime=` param — lazy import, không import runtime mới ở module scope của `agent`.
8. Viết `docs/integrations/<runtime-name>.md` theo template 16-mục.

## Không được làm

- Không đổi kernel mặc định production chỉ vì conformance test pass — cutover là quyết định riêng (cần ADR/xác nhận người dùng), conformance pass chỉ là điều kiện cần.
