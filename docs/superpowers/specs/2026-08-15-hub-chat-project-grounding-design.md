# Hub Chat Project Grounding Design

## Goal

Chat AI (Hub Chat, `chat_execution_service.py`) không được tự bịa tên/trạng thái một Project
rồi dùng lại chính điều nó bịa ra ở các lượt sau trong cùng phiên. Khi người dùng hỏi hoặc
nhắc tới một dự án cụ thể, câu trả lời phải luôn bám theo kết quả tool mới nhất, không phải
trí nhớ hội thoại của model.

## Bug quan sát được

Trong một phiên Hub Chat thật (session `82089411969290240`, brain `80666173057798144`), model
tự ghép tên dự án thành `"MVP Roadmap - mID - Nền tảng định danh và xác thực điện tử"` ngay từ
câu chào đầu tiên - trong khi tên thật trong DB chỉ là `"mID - Nền tảng định danh và xác thực
điện tử"`. Từ đó, mọi lượt tra cứu sau (kể cả khi người dùng yêu cầu "lưu roadmap") đều dùng
lại cái tên bịa này, không khớp `Project.title` thật (`ILIKE '%...%'` không match), tool trả
rỗng, và model - đúng theo luật chống bịa hiện có - báo "không có project". Trong khi đó
project, roadmap (3 MvpStage), OKR cycle và 12-week cycle của dự án này đều **có thật** trong
DB. Cùng phiên, model còn trả lời mâu thuẫn nhau giữa các lượt (lúc nói "không có", lúc mô tả
chi tiết stage) - dấu hiệu nó không gọi lại tool tra cứu ở mọi lượt như kỳ vọng.

## Scope and Decisions

- Chỉ sửa prompt engineering (`GROUNDING_PROMPT` trong `chat_execution_service.py`) và mô tả
  tool (`chat_schema` của `strategy_list_projects` trong `strategy/tools.py`). Không đổi kiến
  trúc tool-calling, không thêm tool mới, không enforce ở tầng code.
- Bắt gọi lại `strategy_list_projects` ở **mọi lượt** nhắc tới một dự án cụ thể, không chỉ lượt
  đầu tiên - đây là lựa chọn tốn thêm 1 tool call/lượt nhưng loại bỏ hẳn kịch bản đã gặp (model
  sai từ lượt đầu rồi lặp lại suốt phiên).
- `list_projects`'s description thêm hướng dẫn: khi không chắc tên chính xác, gọi với `query`
  để trống (liệt kê tất cả) thay vì đoán một chuỗi lọc - vì lọc sai một ký tự là tool trả rỗng
  một cách im lặng.
- Non-goal: không thể đảm bảo 100% model tuân theo prompt (LLM không code-enforced). Đây là cải
  thiện xác suất tuân thủ, không phải một guarantee cứng - nhất quán với cách mọi luật chống
  bịa khác trong file này đang hoạt động.

## Changes

### `chat_execution_service.py::GROUNDING_PROMPT`

Thêm một đoạn quy tắc mới, đặt ngay sau câu "Chưa gọi tool thì bạn CHƯA BIẾT GÌ về workspace
này":

- Mỗi khi nhắc tới một dự án cụ thể (kể cả đã nhắc ở lượt trước), PHẢI gọi lại
  `strategy_list_projects` trong chính lượt đó trước khi khẳng định dự án tồn tại/không tồn
  tại, hay mô tả trạng thái/roadmap của nó.
- Chỉ được dùng đúng `title` mà tool trả về ở lần gọi gần nhất. Không tự diễn giải, rút gọn,
  hay ghép thêm chữ vào tên dự án rồi dùng lại cụm đó ở các lượt sau.

### `strategy/tools.py::list_projects` chat_schema description

Thêm một câu vào `description` của tham số `query`: nếu không chắc chắn tên chính xác, để
`query` trống để lấy toàn bộ danh sách thay vì đoán một cụm lọc - lọc sai dù chỉ một phần cũng
khiến tool trả về rỗng.

## Testing

- Mở rộng `test_chat_execution_service.py` theo đúng pattern của
  `test_worker_tells_the_model_not_to_invent_company_data`: assert các câu quy tắc mới có mặt
  trong `system_turn.content`.
- Mở rộng `test_tool_registry.py` hoặc thêm assertion trong test tool-spec hiện có: kiểm tra
  `list_projects`'s chat_schema description chứa hướng dẫn "để trống query khi không chắc tên".

## Out of Scope

- Server-side enforcement (ví dụ: chặn response nếu không thấy tool call project trước đó).
- Sửa lỗi hiển thị ký tự rác quan sát được một lần trong cùng phiên (`"cyjHiện tại..."`) - chưa
  có root cause, cần một lượt debug riêng nếu tái hiện được.
- Bất kỳ thay đổi nào tới khả năng ghi/tạo dữ liệu của chat - xem
  `2026-08-15-orchestrator-project-cycle-command-design.md` cho phần đó.
