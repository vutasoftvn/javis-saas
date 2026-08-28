# POST-LAUNCH-CONV-001 — Multi-turn conversation context

**Loại:** follow-up (post-launch)
**Owner:** _(chưa gán)_
**Quyết định gốc:** [`ADR-CONV-001`](../architecture/adr/ADR-CONV-001-single-turn-launch.md)
**Điều kiện re-open:** ≥ 3 báo cáo độc lập "agent quên context", hoặc 1 khách hàng chặn, hoặc có bandwidth.

## Vấn đề

Khi launch (ADR-CONV-001), run được dispatch chỉ với `user_prompt` của lượt
hiện tại — agent không nhớ lượt trước dù message đã lưu đầy đủ trong
`PostgresConversationRepository`.

## Scope

1. `apps/cosa/api/routes.py` `POST /agent/conversations/{id}/messages`: nạp
   `plane.conversation_repository.list_messages(conversation_id)`, cắt N lượt
   gần nhất (config `COSA_CONTEXT_MAX_TURNS`, mặc định ~10) hoặc theo token
   budget; đưa vào `input_payload["history"]`.
2. `apps/cosa/worker` + kernel: nhận `history`, prepend vào prompt. Giữ đúng
   contract 3 định danh (`conversation_id != run_id != checkpoint_ref`).
3. `apps/cosa/composition/context_assembler.py`: thêm `ContextFragment`
   lifetime `RUN`, `source_kind="rpc"`, đếm token vào
   `budget_tokens_remaining`.
4. Dọn abstraction chết: xoá hoặc deprecate tường minh
   `apps/cosa/conversations/ports.py` + `stub.py` (hiện không ai dùng).

## Test / DoD

- [ ] `tests/apps/cosa/conversations/test_multi_turn_context.py`: lưu 3 lượt,
  lượt 4 thấy được nội dung lượt 1–3; scope theo `workspace_id` +
  `conversation_id`; cắt đúng N.
- [ ] Golden-path E2E-3: agent nhớ dữ kiện từ lượt trước trong cùng
  conversation.
- [ ] Token budget không âm khi history dài (bị cắt).
- [ ] `make verify` xanh.
