# Rule: Ngôn ngữ phản hồi mặc định là Tiếng Việt

Nguồn chuẩn: [`.kilocode/rules/00-language-vietnamese.md`](../../.kilocode/rules/00-language-vietnamese.md).
File này chỉ mirror để Claude Code (đọc `.agents/rules/`) và Kilo Code dùng chung
một quy tắc. Khi sửa, sửa cả hai file.

## Quy tắc chính

Luôn phản hồi bằng **tiếng Việt** — kể cả khi prompt viết bằng tiếng Anh — trừ
khi người dùng yêu cầu rõ ràng ngôn ngữ khác trong chính lượt đó. Áp dụng cho
giải thích, phân tích, plan, todo list, câu hỏi làm rõ, tóm tắt kết quả, nội dung
`docs/**/*.md` và ADR.

## Giữ tiếng Anh

Tên định danh (class/function/biến/type/file/module), route và endpoint path, tên
field JSON, tên cột DB, tên migration, log message, error code, `APIError`
message, biến môi trường, target `Makefile`, lệnh CLI, tên job CI, và trích dẫn
nguyên văn tài liệu tiếng Anh.

## Không thuộc phạm vi rule này

- **Comment trong code:** theo mục "Comment code" trong [`CLAUDE.md`](../../CLAUDE.md)
  và [`commenting-conventions.md`](../../docs/development/commenting-conventions.md).
- **Canonical prompt của agent runtime** trong [`skillpacks/`](../../skillpacks) và
  [`packages/agent/`](../../packages): instruction prompt vẫn là tiếng Anh, locale
  sản phẩm mặc định là `vi-VN`.
