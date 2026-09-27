# ADR-CONV-002: Nạp lịch sử hội thoại vào prompt

## Status
ACCEPTED + IMPLEMENTED 2026-09-27. Thay thế `ADR-CONV-001-single-turn-launch`.

## Context
`ADR-CONV-001` quyết định launch với chat single-turn: message được lưu đầy đủ nhưng không nạp
lại vào prompt. Với sản phẩm định vị "Co-Founder", đây là khoảng cách UX lớn nhất (review
2026-09-27, G-1): founder phải nhắc lại ngữ cảnh ở mỗi câu. `ConversationHistoryPort` và
`StubConversationHistoryPort` là abstraction chết và chưa từng được khởi tạo.

## Decision
- Worker (`apps/cosa/worker/handlers.py::_load_chat_history`) đọc
  `conversation_repository.list_messages(conversation_id)`. Hàm thuần
  `apps/cosa/conversations/history.py::build_history` giữ các lượt gần nhất:
  - chỉ `user`/`assistant`, trạng thái `completed`;
  - bỏ lượt user của run hiện tại;
  - giới hạn bởi `COSA_CHAT_HISTORY_MESSAGES` (mặc định 12) và `COSA_CHAT_HISTORY_MAX_CHARS`
    (mặc định 12000). Giá trị 0 = single-turn như cũ.
  - Lượt vượt ngân sách bị bỏ từ cũ nhất; mỗi message dài bị cắt ở 2000 ký tự.
  - Message có cấu trúc (`goal_confirm`, `plan_progress`) được rút gọn thành một dòng mô tả,
    không gửi JSON UI thô cho model.
- Lịch sử đi qua `RunRequest.input["history"]` dưới dạng danh sách `{role, content}`.
  - Kernel SDK ghép thành danh sách input item trước lượt hiện tại.
  - `ManualToolLoopKernel` chèn giữa system message và user message.
  - `model_input_guard` vẫn chỉ áp cho lượt mới, vì lịch sử đã qua guard ở lượt của nó.
- Đọc lịch sử lỗi thì run chạy tiếp như single-turn và ghi log; không làm hỏng run.
- Xoá `apps/cosa/conversations/ports.py` và `stub.py`.

## Consequences
- Prompt dài hơn, chi phí token tăng theo ngân sách lịch sử (được ghi vào sổ cái
  `models.run_usage`).
- Chưa có tóm tắt cuốn chiếu cho hội thoại rất dài: lượt vượt ngân sách bị bỏ. Có thể bổ sung
  sau nếu cần, dưới dạng artifact tóm tắt có hash.
- `input_payload` của run lưu cả lịch sử đã giới hạn. Retention/xoá theo subject vẫn áp như
  message gốc.
