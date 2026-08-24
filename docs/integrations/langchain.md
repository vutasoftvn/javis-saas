# Integration: LangChain

## 1. Mục đích

`LangChainKernel` — implementation `ExecutionKernel` dùng LangChain (`ChatDeepSeek` mặc định) làm model provider, theo `ADR-RUNTIME-001` (DRAFT, chờ review).

## 2. Khi nào sử dụng

Chọn tường minh qua `build_cosa_agent_plane(runtime="langchain")` — KHÔNG phải default production (vẫn `OpenAIAgentsKernel`).

## 3. Không dùng cho việc gì

Chưa dùng cho production thật cho tới khi: (a) `ADR-RUNTIME-001` được review/duyệt, (b) pass conformance với DeepSeek provider thật (hiện chỉ test qua fake model).

## 4. Kiến trúc và luồng dữ liệu

Giữ đúng mọi invariant đã harden ở `OpenAIAgentsKernel`: publish spec vào registry trước khi tạo Run, resolve pinned skills trước khi tạo Run, `PromptBundle` cho system message, exact `(run_id, tool_call_id)` không tự sinh lại, typed error (`AgentRuntimeError`) không convert failure thành assistant content.

Dùng `langchain_core.messages` (System/Human/AI/Tool) thay dict thô — checkpoint qua `messages_to_dict`/`messages_from_dict` (giữ đúng `tool_calls` structured, không mất khi serialize).

## 5. Public contracts/API

`agent_integrations.langchain.kernel.LangChainKernel`, `LangChainKernelRunState`. `agent_integrations.langchain.tool_schema_adapter.capability_spec_to_langchain_tool_schema()`.

## 6. Database/schema liên quan

Dùng chung `agent_core.*`/`agent_registry.*` với `OpenAIAgentsKernel` — không có schema riêng.

## 7. Cấu hình

`chat_model=` (mặc định lazy-load `ChatDeepSeek`), `capability_registry=` (để `bind_tools()` cho skill/capability đã pin).

## 8. Ví dụ sử dụng

```python
plane = build_cosa_agent_plane(runtime="langchain", ...)
result = await plane.kernel.run(request, spec)
```

## 9. Cách bổ sung implementation mới

Đổi `chat_model` sang `BaseChatModel` khác (OpenAI, Gemini qua LangChain) — không cần đổi `LangChainKernel`.

## 10. Security/governance

Tool call vẫn đi qua `CapabilityGateway` — LangChain không sở hữu authorization.

## 11. Error handling

`ainvoke()` lỗi → `AgentRuntimeError(MODEL_PROVIDER_ERROR)`, không convert thành assistant content.

## 12. Observability

Cùng event taxonomy với `OpenAIAgentsKernel` (`run.started`, `tool.requested`, ...).

## 13. Testing

`packages/agent_testkit/kernel_conformance/test_langchain_kernel.py` — 5 test (basic response, provider failure typed, tool call exact identity, approval pause/resume, cancellation) dùng `FakeLangChainChatModel` duck-typed.

## 14. Migration/backward compatibility

Package mới hoàn toàn (`packages/agent_integrations/langchain/`), import lazy trong `agent_plane.py` — không bắt buộc cài `langchain-core`/`langchain-deepseek` cho consumer không dùng runtime này.

## 15. Troubleshooting

`ImportError: langchain_core`: cần `pip install langchain-core langchain-deepseek` (không nằm trong `packages/agent_core/requirements.txt`).

## 16. Definition of Done

- [x] Implement đầy đủ Protocol, test conformance qua fake model
- [ ] Test với DeepSeek provider thật (cần API key)
- [ ] Review `ADR-RUNTIME-001`
