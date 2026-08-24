# ADR-RUNTIME-ADAPTERS: `packages/agent_integrations/` là biên giới bắt buộc cho mọi runtime framework

- **Trạng thái:** ACCEPTED — cấu trúc đã tạo và thực thi từ Wave 0/4 (2026-08-24)
- **Ngày quyết định:** 2026-08-24
- **Tác giả:** COSA Core Architecture Team
- **Tham chiếu:**
  - `COSA_AGENT_PLATFORM_IMPLEMENTATION_BLUEPRINT_V2_2026-08-24.md` §4.1, §42, §43
  - `ADR-RUNTIME-001-langchain-deepseek-primary-supersedes-kernel-and-langgraph.md`
  - `packages/agent_integrations/README.md`

---

## 1. Bối cảnh

Trước Wave 0, `packages/` chỉ có `agent_core/` — không có biên giới tách bạch giữa contracts framework-neutral và implementation cụ thể của từng runtime SDK (LangChain, LangGraph, Google ADK, OpenAI Agents SDK, LiteLLM, DeepSeek Harness). Rủi ro nếu không tách: `agent_core` phải cài TẤT CẢ framework dependency dù chỉ dùng 1, và mọi image production phải cõng hết mọi SDK (đúng anti-pattern legacy mà Blueprint V2 §43 cảnh báo).

## 2. Quyết định

1. **`packages/agent_integrations/<runtime>/` là nơi DUY NHẤT được phép import framework SDK cụ thể.** `packages/agent_core` không import `langchain_core`, `litellm`, `google.adk`, `agents` (OpenAI SDK), v.v. — đã verify: `packages/agent_core/requirements.txt` chỉ có `pydantic`, `openai`, `sqlalchemy`, `pyyaml`, `httpx` (Wave 7, cho HTTP client control-plane).
2. **Mỗi runtime con có `pyproject.toml` riêng** (`agent_integrations/langchain/pyproject.toml`, `.../litellm/pyproject.toml`) — không gộp dependency vào 1 file chung ở `agent_integrations/` root (file đó cố ý để trống dependency).
3. **Import framework SDK trong `apps/cosa` PHẢI lazy** (bên trong nhánh code cụ thể, không ở top-level module) — đã áp dụng: `apps/cosa/composition/agent_plane.py` chỉ `from agent_integrations.langchain.kernel import LangChainKernel` bên trong `if runtime == "langchain":`, không phải import top-level.
4. **Mọi adapter mới phải implement contract đã có trong `agent_core.contracts.*`** (`ExecutionKernel`, hoặc tương đương chưa có Protocol riêng như `model_client` interface) — không tự định nghĩa contract song song.
5. **Runtime mới KHÔNG được là default production** cho tới khi pass `agent_testkit/kernel_conformance/` (hoặc conformance suite tương ứng) với provider thật — `runtime="langchain"` hiện là opt-in tường minh qua `build_cosa_agent_plane(runtime=...)`, mặc định vẫn `"openai_agents"`.

## 3. Trạng thái các adapter đã tạo (2026-08-24)

| Adapter | Vị trí | Trạng thái |
|---|---|---|
| LangChain (`LangChainKernel`) | `agent_integrations/langchain/` | Implement đầy đủ `ExecutionKernel`, test qua fake model, CHƯA test DeepSeek thật |
| LiteLLM (`LiteLLMModelClient`) | `agent_integrations/litellm/` | Implement, test qua monkeypatch, CHƯA test API key thật |
| MCP (`capability_adapter.py`) | `agent_integrations/mcp/` | Implement, test qua fake caller |
| A2A (`authority.py`) | `agent_integrations/a2a/` | Implement, test đầy đủ (không cần network) |
| AG-UI (`event_mapper.py`) | `agent_integrations/ag_ui/` | Implement, test qua Run thật, CHƯA certify với AG-UI spec gốc |
| LangGraph | — | **Chưa tạo** — cần đọc lại `langgraph_spike_results.md` trước khi spike (xem `ADR-RUNTIME-001`) |
| Google ADK | — | **Chưa migrate** — production hiện tại ở `legacy/agent_runtime/workforce/agents/orchestration/adk/` (đường dẫn đã sửa 2026-08-24, bản gốc ghi nhầm `legacy/backend/app/workforce/...` — thư mục đó không tồn tại), ngoài `packages/agent_integrations/` |
| OpenAI Agents SDK | — | **Chưa migrate** — `packages/agent_core/kernel/openai_agents_kernel.py` vẫn là manual loop (transitional, theo `ADR-KERNEL` cũ) |
| PydanticAI | — | Xác nhận import được (`pydantic-ai` package), chưa build adapter |

## 4. Hệ quả

Adapter nào CHƯA migrate vào `packages/agent_integrations/` (ADK, OpenAI SDK thật, LangGraph) vẫn là việc tồn đọng — ADR này chốt BIÊN GIỚI kiến trúc, không tự động hoàn thành việc migrate.
