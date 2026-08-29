# ADR-CONV-001: Single-turn conversation context cho launch

## Status
ACCEPTED 2026-08-28 (Lưu ý: ACCEPTED ≠ IMPLEMENTED ≠ WIRED ≠ VERIFIED ≠ PRODUCTION).

## Context

Part 2F đề xuất wire `PostgresConversationHistoryPort` (thay
`StubConversationHistoryPort`) vào `apps/cosa/composition/agent_plane.py`.
Verify bằng code (2026-08-28):

- `apps/cosa/conversations/ports.py::ConversationHistoryPort` +
  `stub.py::StubConversationHistoryPort` **không được khởi tạo ở bất kỳ đâu**
  trong repo. `apps/cosa/composition/context_assembler.py` **không** lắp ráp
  fragment lịch sử hội thoại.
- Persistence hội thoại thật đi qua **`PostgresConversationRepository`**
  (`packages/agent/conversations/`) — **đã được wire** làm
  `CosaAgentPlane.conversation_repository` (`agent_plane.py:245`,
  fail-closed nếu thiếu `AGENT_DATABASE_URL`). Message lưu qua
  `add_message`, đọc qua `list_messages` (dùng ở `routes.py` GET
  conversation/session-view).
- Nhưng khi dispatch run (`routes.py` `POST .../messages`), payload gửi tới
  worker **chỉ chứa `user_prompt = req.content`** — không có lượt trước.
  Worker/kernel chạy run chỉ với lượt hiện tại.

→ Đề xuất 2F.1 nguyên văn nhắm vào abstraction chết. Fix thật (nạp N lượt
gần nhất vào run payload / prompt) đụng `routes.py` + `apps/cosa/worker` +
đường build prompt của kernel — rủi ro hồi quy cao hơn mức "chi phí thấp" mà
plan giả định, và cần test kỹ trên đường golden-path.

## Decision

**Launch với single-turn context.** Không wire history port trước go-live.

- Giữ `PostgresConversationRepository` như hiện tại (message vẫn được **lưu**
  đầy đủ — không mất dữ liệu, chỉ là không **nạp lại** vào prompt).
- Xoá / đánh dấu deprecated `apps/cosa/conversations/ports.py` +
  `stub.py` trong lần dọn sau (abstraction chết, gây hiểu nhầm) — KHÔNG làm
  trong nhánh này để giữ thay đổi tối thiểu.
- Hệ quả UX: agent **không nhớ lượt trước trong cùng conversation**. Người
  dùng phải nhắc lại ngữ cảnh mỗi lượt. Chấp nhận cho MVP; thông báo rõ
  trong release note.

## Điều kiện re-open

Bất kỳ điều nào:
- Phản hồi người dùng prod về việc "agent quên context" đạt ngưỡng
  (≥ 3 báo cáo độc lập hoặc 1 khách hàng chặn).
- Có bandwidth cho follow-up ticket `POST-LAUNCH-CONV-001`.

## Follow-up

`docs/tickets/POST-LAUNCH-CONV-001-multi-turn-context.md` — scope:
- `routes.py` `POST .../messages`: nạp `list_messages(conversation_id)`, cắt
  N lượt gần nhất (hoặc token budget), đưa vào `input_payload`.
- `apps/cosa/worker` + kernel: nhận history, prepend vào prompt theo đúng
  contract 3 định danh (`conversation_id != run_id != checkpoint_ref`).
- `context_assembler.py`: thêm `ContextFragment` lifetime `RUN` cho history,
  đếm token vào budget.
- Test: `tests/apps/cosa/conversations/test_multi_turn_context.py` +
  golden-path E2E-3 (agent nhớ lượt trước).

## Relates
- Part 2F (`docs/implementation/2026-08-28-tpr-part2f-deferred-decisions.md`).
- `docs/implementation/readiness-reporting-standard.md` §"Deferred".
