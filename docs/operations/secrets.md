# Vận hành: Secrets

## Secret bắt buộc theo module (đã xác nhận qua code, không phải giả định)

| Secret | Dùng ở đâu | Bắt buộc? |
|---|---|---|
| `AGENT_CORE_DATABASE_URL` | `packages/agent_core` mọi repository factory (`get_run_repository()`, `get_memory_store()`, `get_knowledge_store()`, `get_governance_store()`, `get_spec_registry()`...) | Bắt buộc production — thiếu → `RuntimeError` khi khởi động (no-silent-fallback, xác nhận đúng chủ đích, không phải bug). |
| `DEEPSEEK_API_KEY` | `LangChainKernel` (qua `langchain-deepseek`), `LiteLLMModelClient` khi route `model="deepseek-*"` | Chỉ bắt buộc nếu dùng runtime LangChain/DeepSeek — CHƯA có key thật trong môi trường dev phiên này, `LangChainKernel` mới test bằng fake chat model. |
| OpenAI/Anthropic API key (biến cụ thể tuỳ provider) | `OpenAIAgentsKernel` model client hiện tại | Bắt buộc cho kernel production hiện dùng — không đổi trong phiên này. |
| Encore secrets (`encore secret set`) | `services/cosa`, `services/company` | Quản lý qua Encore secret manager, KHÔNG qua `.env` — chưa verify trong phiên này (không có Encore CLI). |

## Nguyên tắc

- Không commit secret vào git — kiểm tra `git status`/nội dung file trước khi `git add` bất kỳ file nào trông giống config (CLAUDE.md an toàn sửa code + system-level rule "double-check file contents before pushing").
- Không log giá trị secret ra `RunEventRecord`/structured log — chỉ log tên biến/provider, không log giá trị.
- Email người dùng (`vutasoft@gmail.com`) chỉ dùng để attribution/định danh tác giả — không gửi tới service không liên quan.

## CHƯA làm trong phiên này

- Chưa thiết lập secret rotation policy.
- Chưa xác nhận Encore secret manager đã có entry cho control-plane mới (Wave 7) — endpoint mới không tự cần secret riêng (dùng chung DB connection Encore quản lý), nhưng chưa verify thật.
