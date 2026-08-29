# Integration: OpenAI Agents SDK

## Cập nhật 2026-08-24: đã có adapter thật, chưa phải default

`packages/agent_integrations/openai_agents_sdk/kernel.py` (class
`RealOpenAIAgentsSDKKernel`) — implement `ExecutionKernel` Protocol dùng
`agents.Runner`/`agents.Agent` THẬT (package `openai-agents==0.22.0`), khác
tên với `OpenAIAgentsKernel` (manual loop, mô tả ở dưới — vẫn là kernel mặc
định production, KHÔNG đổi). 5 test conformance
(`packages/agent_testkit/kernel_conformance/test_openai_agents_sdk_kernel.py`)
pass với fake model + 1 test gọi DeepSeek thật qua
`agents.extensions.models.litellm_model.LitellmModel`
(`test_openai_agents_sdk_kernel_deepseek_live.py`, skip nếu thiếu
`DEEPSEEK_API_KEY`). Checkpoint dùng `RunState.to_json()`/`from_json()` —
lưu ý tên gọi gây hiểu nhầm: trả về `dict`, KHÔNG phải chuỗi JSON (bug thật
đã fix khi viết kernel này). Chưa wire vào `apps/cosa/composition/`, chỉ tồn
tại như adapter tuỳ chọn đã pass conformance.

## Trạng thái kernel mặc định: kernel hiện tại là manual loop, KHÔNG phải SDK thật

`packages/agent/kernel/openai_agents_kernel.py` (class `OpenAIAgentsKernel`) tên gọi gây hiểu lầm — đây là 1 reasoning loop TỰ VIẾT (gọi model client trực tiếp, tự parse tool call, tự lặp `_run_reasoning_turns`), **không import package `openai-agents` (Agents SDK) thật**. Đây là phát hiện đã ghi nhận từ đầu phiên (mục A1 trong bảng hiệu chỉnh, xem `COSA_AGENT_PLATFORM_BLUEPRINT_V2_RECONCILED_PLAN_2026-08-24.md` Phần A).

## Vì sao vẫn là kernel mặc định

`ADR-KERNEL-openai-agents-sdk-ratification.md` (trước đây) ratify hướng này làm kernel chính. `ADR-RUNTIME-001-langchain-deepseek-primary-supersedes-kernel-and-langgraph.md` (2026-08-24, DRAFT — **chưa duyệt**) đảo hướng runtime chính sang LangChain, nhưng cho tới khi ADR-RUNTIME-001 được duyệt chính thức, `OpenAIAgentsKernel` (manual loop) vẫn là implementation `ExecutionKernel` production hiện tại — `LangChainKernel` (Wave 4) là candidate mới, chưa cutover.

## Việc CHƯA làm (thật, không phải kế hoạch)

- Không có package `openai-agents` trong bất kỳ `requirements.txt`/`pyproject.toml` nào trong repo.
- Không có migration path sang SDK thật — nếu muốn dùng SDK thật (`Agent`, `Runner` class của package `openai-agents`), cần viết kernel MỚI (`packages/agent_integrations/openai_agents_sdk/kernel.py`), implement cùng `ExecutionKernel` Protocol, và chạy qua `agent_testkit/kernel_conformance/` như đã làm với `LangChainKernel` — không sửa `openai_agents_kernel.py` tại chỗ vì tên class đó đã được dùng ở nhiều composition root (`apps/cosa/composition/agent_plane.py`).

## Định hướng

Xem `ADR-RUNTIME-001-...md` — SDK thật (nếu build) sẽ nằm trong `packages/agent_integrations/`, không phải `packages/agent/kernel/` (đúng dependency rule: `agent` không được phụ thuộc SDK bên thứ 3 cụ thể).
