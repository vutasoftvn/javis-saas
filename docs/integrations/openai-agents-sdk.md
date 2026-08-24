# Integration: OpenAI Agents SDK

## Trạng thái: kernel hiện tại là manual loop, KHÔNG phải SDK thật

`packages/agent_core/kernel/openai_agents_kernel.py` (class `OpenAIAgentsKernel`) tên gọi gây hiểu lầm — đây là 1 reasoning loop TỰ VIẾT (gọi model client trực tiếp, tự parse tool call, tự lặp `_run_reasoning_turns`), **không import package `openai-agents` (Agents SDK) thật**. Đây là phát hiện đã ghi nhận từ đầu phiên (mục A1 trong bảng hiệu chỉnh, xem `COSA_AGENT_PLATFORM_BLUEPRINT_V2_RECONCILED_PLAN_2026-08-24.md` Phần A).

## Vì sao vẫn là kernel mặc định

`ADR-KERNEL-openai-agents-sdk-ratification.md` (trước đây) ratify hướng này làm kernel chính. `ADR-RUNTIME-001-langchain-deepseek-primary-supersedes-kernel-and-langgraph.md` (2026-08-24, DRAFT — **chưa duyệt**) đảo hướng runtime chính sang LangChain, nhưng cho tới khi ADR-RUNTIME-001 được duyệt chính thức, `OpenAIAgentsKernel` (manual loop) vẫn là implementation `ExecutionKernel` production hiện tại — `LangChainKernel` (Wave 4) là candidate mới, chưa cutover.

## Việc CHƯA làm (thật, không phải kế hoạch)

- Không có package `openai-agents` trong bất kỳ `requirements.txt`/`pyproject.toml` nào trong repo.
- Không có migration path sang SDK thật — nếu muốn dùng SDK thật (`Agent`, `Runner` class của package `openai-agents`), cần viết kernel MỚI (`packages/agent_integrations/openai_agents_sdk/kernel.py`), implement cùng `ExecutionKernel` Protocol, và chạy qua `agent_testkit/kernel_conformance/` như đã làm với `LangChainKernel` — không sửa `openai_agents_kernel.py` tại chỗ vì tên class đó đã được dùng ở nhiều composition root (`apps/cosa/composition/agent_plane.py`).

## Định hướng

Xem `ADR-RUNTIME-001-...md` — SDK thật (nếu build) sẽ nằm trong `packages/agent_integrations/`, không phải `packages/agent_core/kernel/` (đúng dependency rule: `agent_core` không được phụ thuộc SDK bên thứ 3 cụ thể).
