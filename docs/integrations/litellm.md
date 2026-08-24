# Integration: LiteLLM

## 1. Mục đích

`LiteLLMModelClient` — Model Gateway (Blueprint V2 §7) bọc `litellm.acompletion()` thành interface `.chat.completions.create()` tương thích OpenAI, dùng làm `model_client=` cho `OpenAIAgentsKernel` mà không cần đổi kernel.

## 2. Khi nào sử dụng

Khi cần routing/fallback/cost tracking tập trung giữa nhiều provider (DeepSeek/OpenAI/Gemini/Claude/local) thay vì gọi 1 provider trực tiếp.

## 3. Không dùng cho việc gì

Chưa test với API key thật — chưa dùng cho production tới khi verify.

## 4. Kiến trúc và luồng dữ liệu

```
OpenAIAgentsKernel._call_model()
  → self._client.chat.completions.create(...)  # self._client = LiteLLMModelClient
    → litellm.acompletion(model, messages, fallbacks=[...], ...)
    → map exception: RateLimitError→MODEL_RATE_LIMIT, ContextWindowExceededError→CONTEXT_LIMIT_EXCEEDED,
      Timeout→MODEL_TIMEOUT, AuthenticationError→TENANT_UNAUTHORIZED, khác→MODEL_PROVIDER_ERROR
```

Kernel giữ nguyên `AgentRuntimeError` typed từ client (fix: `except AgentRuntimeError: raise` trước `except Exception` rộng trong `_call_model`).

## 5. Public contracts/API

`agent_integrations.litellm.gateway.LiteLLMModelClient(model, fallbacks, **default_kwargs)`.

## 6. Database/schema liên quan

Không có.

## 7. Cấu hình

Credential provider qua biến môi trường litellm chuẩn (`DEEPSEEK_API_KEY`, `OPENAI_API_KEY`, ...) — không truyền secret qua code.

## 8. Ví dụ sử dụng

```python
client = LiteLLMModelClient(model="deepseek-chat", fallbacks=["openai/gpt-4o-mini"])
kernel = OpenAIAgentsKernel(repository=repo, model_client=client)
```

## 9. Cách bổ sung implementation mới

Không cần — litellm tự hỗ trợ provider mới qua tên model string chuẩn của nó.

## 10. Security/governance

Không tự quyết governance — chỉ là model call layer.

## 11. Error handling

Xem §4 — mapping exception cụ thể, không generic hoá quá mức.

## 12. Observability

Chưa wire cost/usage vào `run_model_calls` (bảng đó chưa tồn tại trong schema hiện tại — Blueprint V2 đề xuất, chưa tạo).

## 13. Testing

`packages/agent_testkit/model_conformance/test_litellm_gateway.py` — monkeypatch `litellm.acompletion`, verify response pass-through + exception mapping + kernel giữ đúng error code cụ thể.

## 14. Migration/backward compatibility

Package mới, dependency `litellm>=1.97.0` riêng trong `agent_integrations/litellm/pyproject.toml`.

## 15. Troubleshooting

Lỗi generic `MODEL_PROVIDER_ERROR` thay vì code cụ thể: kiểm tra kernel có bị revert fix "giữ nguyên AgentRuntimeError" không.

## 16. Definition of Done

- [x] Wrapper + exception mapping, test qua monkeypatch
- [ ] Test API key thật, tuning fallback/retry cho tải production
