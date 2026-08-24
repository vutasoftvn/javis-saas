# packages/agent_integrations

Nơi chứa các implementation cụ thể của contracts framework-neutral khai báo trong `packages/agent_core/contracts/` (`ExecutionKernel`, `ModelProvider`, `WorkflowRuntime`, `SandboxProvider`) cho từng runtime/framework bên ngoài (LangChain, LangGraph, Google ADK, OpenAI Agents SDK, DeepSeek Harness, LiteLLM, MCP, A2A, AG-UI, OpenTelemetry).

## Quy tắc bắt buộc

1. **`packages/agent_core` không được import bất cứ thứ gì từ đây.** Chiều phụ thuộc chỉ một chiều: `agent_integrations/*` → implement `agent_core.contracts.*`.
2. **Mỗi subfolder (`langchain/`, `langgraph/`, `google_adk/`, `openai_agents/`, `deepseek_harness/`, `litellm/`, `mcp/`, `a2a/`, `ag_ui/`, `otel/`, `sandboxes/`) có `pyproject.toml`/dependency riêng.** Không cài tất cả framework vào cùng 1 image production — xem `COSA_AGENT_PLATFORM_BLUEPRINT_V2_RECONCILED_PLAN_2026-08-24.md` Phần F (Wave 4) và Blueprint V2 §43.
3. **Mọi side effect vẫn phải đi qua `packages/agent_core/capabilities/gateway.py`.** Runtime adapter chỉ được phát sinh intent (`ToolInvocation`), không tự thực thi capability.
4. **Runtime mới phải pass `agent_testkit/kernel_conformance/`** (hoặc conformance suite tương ứng) trước khi được chọn làm default trong `apps/cosa/composition/agent_plane.py`.

## Trạng thái hiện tại (2026-08-24)

- Package này vừa được scaffold (Wave 0.2), chưa có implementation nào.
- Runtime chính theo `ADR-RUNTIME-001-langchain-deepseek-primary-supersedes-kernel-and-langgraph.md` (draft, chờ review) là `langchain/` — sẽ triển khai ở Wave 4.
- Google ADK integration hiện tại **chưa** nằm trong package này — vẫn đang chạy production ở `legacy/backend/app/workforce/agents/orchestration/adk/` theo `docs/agent-platform/ADK_INTEGRATION.md`. Việc di chuyển vào `agent_integrations/google_adk/` là việc của Wave 10, không phải bây giờ.

Xem `COSA_AGENT_PLATFORM_BLUEPRINT_V2_RECONCILED_PLAN_2026-08-24.md` Phần F, I để biết chi tiết từng Wave.
