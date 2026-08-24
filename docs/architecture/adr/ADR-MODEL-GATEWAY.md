# ADR-MODEL-GATEWAY: LiteLLM làm Model Gateway trung tâm

- **Trạng thái:** ACCEPTED — implement 1 phần ở Wave 4 (2026-08-24), chưa test với API key thật
- **Ngày quyết định:** 2026-08-24
- **Tác giả:** COSA Core Architecture Team
- **Tham chiếu:**
  - `COSA_AGENT_PLATFORM_IMPLEMENTATION_BLUEPRINT_V2_2026-08-24.md` §7
  - `COSA_AGENT_PLATFORM_BLUEPRINT_V2_RECONCILED_PLAN_2026-08-24.md` Phần F (Wave 4)
  - `ADR-RUNTIME-001-langchain-deepseek-primary-supersedes-kernel-and-langgraph.md`

---

## 1. Bối cảnh

Trước Wave 4, `OpenAIAgentsKernel` gọi model provider trực tiếp qua raw `openai` client (`self._client.chat.completions.create(...)`) — không có routing/fallback/cost tracking tập trung. `legacy/agent_runtime/cosa_core/reliability/litellm_invoker.py` (đường dẫn đã sửa 2026-08-24, bản gốc ghi nhầm `legacy/backend/.../litellm_invoker.py` — thư mục đó không tồn tại; frozen, không phát triển tiếp theo ADR-012/013) đã có kinh nghiệm circuit breaker/fallback provider với LiteLLM nhưng chưa port vào `packages/agent_core`.

## 2. Quyết định

1. **LiteLLM là Model Gateway layer** giữa `ExecutionKernel` và provider thật (DeepSeek/OpenAI/Gemini/Claude/local), theo đúng kiến trúc Blueprint V2 §7: `ExecutionKernel → ModelProvider → LiteLLM Gateway → Provider`.
2. **Chưa tạo `ModelProvider` Protocol riêng** (quyết định Wave 3, tránh premature abstraction khi chưa có 2+ consumer thật cần nó) — thay vào đó `LiteLLMModelClient` (`packages/agent_integrations/litellm/gateway.py`) implement TRỰC TIẾP interface `.chat.completions.create(...)` tương thích OpenAI mà `OpenAIAgentsKernel`/model_client param đã chấp nhận sẵn — dùng làm drop-in `model_client=` không cần đổi kernel.
3. **Failure ownership** (Blueprint V2 §7 bảng): provider HTTP/5xx/rate-limit/timeout/context-limit → LiteLLM/`LiteLLMModelClient` map thành `AgentRuntimeError` với `RuntimeErrorCode` cụ thể (`MODEL_RATE_LIMIT`, `CONTEXT_LIMIT_EXCEEDED`, `MODEL_TIMEOUT`, `TENANT_UNAUTHORIZED`); tool validation → Agent Core (Gateway); workflow/business retry → tầng tương ứng, không nested retry chaos.
4. **`OpenAIAgentsKernel._call_model()` phải giữ nguyên `AgentRuntimeError` đã typed từ model_client thông minh** — không re-wrap thành `MODEL_PROVIDER_ERROR` chung chung (fix cụ thể: `except AgentRuntimeError: raise` trước `except Exception` rộng).

## 3. Hệ quả

### Tích cực
- Routing/fallback/cost tracking tập trung qua LiteLLM thay vì tự viết circuit breaker riêng.
- Không cần `ModelProvider` Protocol mới — giảm surface area, dùng lại interface `model_client` đã có.

### Rủi ro & biện pháp
- **Chưa test với API key thật** — `packages/agent_testkit/model_conformance/test_litellm_gateway.py` chỉ monkeypatch `litellm.acompletion`, chưa chạy qua DeepSeek/OpenAI thật. Cần chạy trước khi coi là production-ready.
- **`LiteLLMModelClient` không tự có circuit breaker riêng** — dựa hoàn toàn vào cơ chế `fallbacks=`/retry sẵn có của litellm, chưa tuning tham số (max_retries, cooldown) cho tải thật.
