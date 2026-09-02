# Rule: Ngôn ngữ phản hồi mặc định là Tiếng Việt

Phạm vi: **mọi mode** (Architect, Code, Ask, Debug, Orchestrator, Review) và mọi
subtask sinh ra từ `new_task`.

## 1. Quy tắc chính

Luôn phản hồi bằng **tiếng Việt**, kể cả khi người dùng viết prompt bằng tiếng
Anh, trừ khi người dùng yêu cầu rõ ràng ngôn ngữ khác trong chính lượt đó.

Áp dụng cho: giải thích, phân tích, lập kế hoạch, todo list, câu hỏi làm rõ
(`ask_followup_question`), tóm tắt kết quả (`attempt_completion`), nội dung
`docs/**/*.md` và ADR.

## 2. Phần BẮT BUỘC giữ tiếng Anh

Không dịch những thành phần sau — dịch sẽ làm sai code, sai grep, sai contract:

- Tên định danh: class, function, biến, type, enum value, tên file, tên module.
- Route / endpoint path, tên field JSON, tên cột DB, tên migration.
- Thông báo lỗi hệ thống, log message, error code, `APIError` message.
- Tên biến môi trường, target trong `Makefile`, lệnh CLI, tên job CI.
- Trích dẫn nguyên văn tài liệu / spec tiếng Anh (giữ nguyên, không dịch lại).
- Commit message: theo convention hiện có của repo, rule này không đổi.

Cách viết đúng: câu tiếng Việt bao quanh, thuật ngữ kỹ thuật giữ nguyên tiếng Anh.

> Handler `createLead` phải trả `APIError.invalidArgument` khi thiếu `company_id`,
> không throw `Error` trần.

## 3. Comment trong code

Comment trong code **không** do rule này quy định. Nguồn chuẩn là mục
"Comment code" trong [`CLAUDE.md`](../../CLAUDE.md) và
[`commenting-conventions.md`](../../docs/development/commenting-conventions.md):
mặc định không viết comment, chỉ viết khi WHY không hiển nhiên; phần WHY viết
tiếng Việt, định danh và log giữ tiếng Anh.

Rule này chỉ mở rộng sang phần hội thoại và tài liệu, không tạo quy ước mới cho
comment.

## 4. Không xung đột với prompt tiếng Anh của runtime

Đây là quy ước giao tiếp giữa agent và developer. Nó **không** áp dụng cho
canonical prompt của agent runtime trong [`skillpacks/`](../../skillpacks) và
[`packages/agent/`](../../packages) — theo kiến trúc COSA, instruction prompt
canonical vẫn là tiếng Anh, locale sản phẩm mặc định là `vi-VN`.
