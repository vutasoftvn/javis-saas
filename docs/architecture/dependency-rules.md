# Quy tắc phụ thuộc (Dependency Rules)

## Chiều phụ thuộc bắt buộc

```
apps/cosa
  ↓
packages/agent_integrations/*  (LangChain, LiteLLM, MCP, A2A, AG-UI, ...)
  ↓ implement contracts của
packages/agent_core/contracts/*
  ↑
packages/agent_core/{runs,capabilities,governance,memory,knowledge,skills,registry,conversations,prompts}/*
```

## Quy tắc đã verify trong code (2026-08-24)

1. **`packages/agent_core` KHÔNG import framework SDK cụ thể.** Verify: `packages/agent_core/requirements.txt` chỉ có `pydantic`, `openai`, `sqlalchemy`, `pyyaml`, `httpx`. Không có `langchain_core`, `litellm`, `google.adk`.
2. **`packages/agent_integrations/*` là nơi DUY NHẤT import framework SDK.** Mỗi runtime con có `pyproject.toml` riêng — không gộp dependency chung.
3. **Import framework SDK trong `apps/cosa` phải lazy.** Verify: `apps/cosa/composition/agent_plane.py` chỉ `from agent_integrations.langchain.kernel import LangChainKernel` bên trong nhánh `if runtime == "langchain":`.
4. **`contracts/` không phụ thuộc ngược vào subsystem cụ thể.** Verify: `PinnedSkillRef` đặt ở `packages/agent_core/contracts/identity.py` (không phải `skills/`) chính vì lý do này — `skills/contracts.py` import TỪ `contracts/identity.py`, không phải chiều ngược lại.
5. **`agent_core` (Python) không SQL trực tiếp vào business schema `services/company`/`services/cosa`.** Giao tiếp qua HTTP internal RPC nếu cần (`HttpControlPlaneLeaseClient`, Wave 7).
6. **`services/cosa` (TypeScript) không SQL trực tiếp vào schema Python** (`agent_core.*`, `agent_memory.*`, ...).
7. **Mọi side effect qua `CapabilityGateway`** — runtime adapter (bao gồm MCP) chỉ phát sinh intent, không tự thực thi.

## Vi phạm đã tìm và sửa trong phiên 2026-08-24

- `OpenAIAgentsKernel._execute_tool()` từng tự sinh `run_id`/`tool_call_id` MỚI trong nhánh fallback, phá vỡ identity xuyên suốt kernel→gateway — đã sửa (xem `ADR-DURABLE-IDENTITY.md`).
- `CapabilityGateway` từng có governance accumulator in-memory RIÊNG thay vì dùng `GovernanceStateStore` chung đã có sẵn (dùng bởi `workflows/`) — đã sửa.

## Cách kiểm tra chưa tự động hoá

Chưa có architecture test (import-linter hoặc tương đương) enforce các quy tắc trên tự động trong CI — hiện dựa vào code review + tài liệu này. Đây là việc tồn đọng (Blueprint V2 Wave 0 gợi ý "tạo architecture tests cho dependency direction", chưa làm).
