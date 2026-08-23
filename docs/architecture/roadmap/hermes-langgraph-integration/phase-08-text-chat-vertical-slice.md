# Phase 8 — Vertical Slice 1 + 2: Repair/Replace Text Chat Integration

> Nguồn gốc: `COSA_AGENT_PLATFORM_PROMOTION_IMPLEMENTATION_PLAN_2026-08-23.md` §"Phase 8" (Step 10, reframed). Bổ sung Hermes/LangGraph theo `COSA_HERMES_LANGGRAPH_INTEGRATION_PLAN_2026-08-23.md` §3.

## Mục tiêu

Flutter Text Chat nói chuyện được với `apps/cosa/api` thật, qua đúng 2 vertical slice acceptance criteria của Master doc — và (mới) contract tối thiểu cho conversation history recall được định nghĩa, sẵn sàng cho Phase 9.

## Điều kiện tiên quyết

Phase 7 xong (có `apps/cosa/api` với ít nhất 1 read + 1 write capability, context assembler thật).

## Việc cụ thể (gốc) — thứ tự bắt buộc

1. **Audit contract cũ trước khi đổi:** đọc đầy đủ `/agent/*` HTTP schema (`agentos/api/chat/routes.py`, `schemas.py`) + SSE event vocabulary + toàn bộ `AgentChatService` (Dart) — liệt kê từng endpoint, field, event type đang được Flutter dùng thật.
2. Viết bảng quyết định: mỗi endpoint/field cũ → giữ nguyên / đổi có lý do / bỏ có lý do — lưu vào `docs/architecture/agentos_salvage_inventory.md` mục "Phase 8 contract decision".
3. Implement `apps/cosa/api/` theo quyết định ở bước 2, dùng contract `RunRequest`/`RunResult`/events từ Phase 1–2.
4. **Bổ sung observability tường minh trước khi rewire:** sửa `AgentChatService.getConversations()` (và các method catch-and-swallow khác) để lỗi network/backend không còn tự động biến thành `[]` — thêm log/metric phân biệt "không có data" và "gọi API thất bại".
5. Sửa `frontend/lib/modules/chat/services/agent_chat_service.dart` trỏ `agentOsBaseUrl` sang endpoint mới của `apps/cosa/api`.
6. Vertical Slice 1 (Read Path): Flutter → Agent API → durable Run → pinned AgentSpec → OpenAIAgentsKernel → DeepSeek route → read-only Capability (Phase 7) → `services/company` → streamed events → final answer + usage/trace. Acceptance criteria: unique run id, spec manifest persisted, tool call id stable, read-only policy ALLOW, streaming thật, trace/usage persisted, cancel works, provider error map predictably, không import business DB từ Agent Core.
7. Vertical Slice 2 (Write + Approval + Restart): full canonical test, dùng write capability từ Phase 7, qua approval flow Phase 5.

## Bổ sung Hermes/LangGraph — Conversation History Port (contract only)

**Lý do:** khi audit `AgentChatService.getConversations()` ở bước 1 (gốc), xác định luôn: Flutter hiện lưu conversation history local hay fetch từ agent API? Câu trả lời quyết định Phase 9 có cần implement đầy đủ `apps/cosa/conversations/` hay không.

**Việc cụ thể:**

1. Định nghĩa contract (chỉ Protocol, chưa implement thật):
   ```python
   # apps/cosa/conversations/ports.py
   class ConversationHistoryPort(Protocol):
       async def recent_messages(self, conversation_id: str, limit: int) -> list[Message]: ...
       async def search_messages(self, conversation_id: str, query: str) -> list[Message]: ...
       async def get_thread_context(self, run_id: str, limit: int) -> list[Message]: ...
   ```
2. Đăng ký stub implementation trong composition (Phase 7's `apps/cosa/composition/`) trả về danh sách rỗng — không phá vỡ luồng Flutter hiện có khi contract chưa có data thật.
3. Giữ tách biệt rõ 3 identity, không collapse cho tiện: `conversation_id ≠ run_id ≠ workflow execution thread/checkpoint id` — đây là invariant quan trọng từ supplement gốc §10.3, verify rằng route mới ở bước 3 (gốc) không vô tình dùng `run_id` làm `conversation_id`.

## Definition of Done — Phase 8

**Gốc:**
- Integration test end-to-end thật (không mock backend) chạy Flutter test hoặc ít nhất HTTP-level test giả lập đúng request Flutter gửi, xác nhận toàn bộ acceptance criteria Vertical Slice 1 + 2.
- Bảng quyết định contract cũ→mới đã có, không có endpoint nào bị đổi "âm thầm" mà không ghi lý do.
- `AgentChatService` không còn silent-swallow lỗi thành `[]` mà không phân biệt được với "thật sự trống".

**Bổ sung:**
- `apps/cosa/conversations/ports.py` tồn tại với `ConversationHistoryPort`, stub implementation đăng ký trong composition, không phá vỡ Flutter integration test ở trên.
- Xác nhận trong bảng quyết định (bước 2, gốc): `conversation_id`/`run_id`/checkpoint identity không bị collapse ở bất kỳ endpoint nào của `apps/cosa/api`.

## Rủi ro/lưu ý

**Gốc:** Đây là phase đầu tiên chạm UI thật — cần user xác nhận trước khi merge/deploy vì ảnh hưởng trải nghiệm người dùng cuối, dù hiện tại chưa ai dùng thật (theo audit).

**Bổ sung:** Không implement conversation search/FTS thật ở phase này (đó là Phase 9) — chỉ contract + stub, tránh scope creep vào một phase đã có acceptance criteria nặng (2 vertical slice).
