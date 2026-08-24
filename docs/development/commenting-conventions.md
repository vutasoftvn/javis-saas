# Quy ước comment code

Nguồn chuẩn: CLAUDE.md mục "Comment code". File này chỉ mở rộng ví dụ cụ thể, không thay thế CLAUDE.md.

## Quy tắc

- Giải thích WHY (lý do/ý nghĩa) → tiếng Việt.
- Tên định danh (function/class/variable), thông báo lỗi hệ thống/log, trích dẫn nguyên văn tài liệu tiếng Anh → giữ tiếng Anh.
- Không bắt buộc viết lại comment cũ ngay — áp dụng cho comment mới, chuyển dần khi sửa file đó.
- Mặc định KHÔNG viết comment (theo nguyên tắc chung của phiên này) — chỉ viết khi WHY không hiển nhiên: 1 constraint ẩn, 1 invariant tinh vi, workaround cho bug cụ thể, hành vi gây bất ngờ cho người đọc. Không giải thích WHAT (tên định danh tốt đã tự nói).

## Ví dụ thật trong codebase (từ phiên Wave 0-11)

Comment ĐÚNG (giải thích WHY, có invariant tinh vi):
```python
# Idempotency claim đã tồn tại có thể là "cùng invocation đang resume"
# (run_id + tool_call_id khớp) hoặc "invocation khác đang race" — phải phân biệt
# 2 trường hợp này, không được coi mọi claim trùng là IN_PROGRESS.
if record.run_id == claim.run_id and record.tool_call_id == claim.tool_call_id:
    ...
```

Comment SAI (giải thích WHAT, thừa vì tên đã rõ):
```python
# Lấy governance state từ store
state = await self._governance_store.load_governance_state(...)
```

## Áp dụng cho ADR/doc

ADR và `docs/**/*.md` viết bằng tiếng Việt (trừ trích dẫn nguyên văn tiếng Anh, tên field/class/API giữ nguyên). Đây là quy ước đã áp dụng nhất quán cho toàn bộ tài liệu viết trong phiên Wave 0-11.
