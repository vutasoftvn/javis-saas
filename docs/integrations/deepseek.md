# Integration: DeepSeek

## Trạng thái: không phải 1 "integration" riêng — là model route qua LiteLLM/LangChain

Khác các integration khác trong thư mục này, DeepSeek KHÔNG có package `packages/agent_integrations/deepseek/` riêng — theo đúng nguyên tắc Blueprint V2 §24 ("Model selection thuộc ModelPolicy/resolver, không hard-code thành architecture"). DeepSeek được truy cập qua 2 đường:

1. **`LiteLLMModelClient`** (`docs/integrations/litellm.md`) — `model="deepseek-chat"` truyền vào constructor, litellm tự route tới DeepSeek API.
2. **`LangChainKernel`** (`docs/integrations/langchain.md`) — `_resolve_chat_model()` mặc định lazy-load `ChatDeepSeek` từ package `langchain-deepseek` khi không truyền `chat_model=` tường minh.

## Đã cài đặt, chưa test với API key thật

`langchain-deepseek` đã cài và import được trong môi trường phát triển (2026-08-24) — chưa gọi API thật (không có `DEEPSEEK_API_KEY`).

## Việc cần làm

Chạy `test_deepseek_compatibility_matrix.py` (đã tồn tại từ trước phiên này, `tests/agent_core/kernel/`) với `LangChainKernel`/`LiteLLMModelClient` thật, không chỉ mock — hiện matrix đó chỉ test `OpenAIAgentsKernel` với mock client.
