# Độ tin cậy của chat agent Co-Founder — thiết kế

Ngày: 2026-09-26. Phạm vi: luồng chat Co-Founder (Flutter hub → COSA `/agent/*` → worker → kernel → LiteLLM/tool).

## Bối cảnh

Sau fix SSE 404 (commit `3400b698`), chat chạy được tới bước gọi LLM và lộ ra 3 nhóm lỗi:

1. Provider trả `Insufficient Balance` (DeepSeek trực tiếp) — UI hiện nguyên chuỗi litellm thô.
2. Tool `workspace.context.read` lỗi 422 `unknown variables: ['query']` làm cả run thất bại.
3. Model không biết `workspace_id`/`project_id` nên hỏi lại người dùng; các endpoint dashboard trả HTTP 500.

Model chat được chọn qua `WorkspaceModelPolicy` trong DB (không phải `.env`); policy đã có `fallback_profile_ids`.

## Các hạng mục (độc lập, commit riêng)

### 1. Phân loại lỗi provider
- Module mới `packages/agent/kernel/provider_errors.py`: `classify_provider_error(exc) -> (code, user_message_vi)`.
- Mã: `provider_insufficient_balance`, `provider_auth`, `provider_rate_limited`, `provider_unavailable`, `unknown`. Nhận diện theo kiểu exception litellm + nội dung ("Insufficient Balance", 401, 429, 5xx).
- Kernel (`openai_agents_kernel.py` ~L510; langchain/pydantic_ai nếu chung đường emit) thêm `error_code` và `user_message` vào payload `run.failed`. Chuỗi thô chỉ ghi log.

### 2. Fallback model
- Khi gọi LLM lỗi thuộc `insufficient_balance | auth | unavailable`, thử lần lượt các profile trong `fallback_profile_ids` của policy đã resolve (chỉ profile ACTIVE trong workspace), rồi mới emit `run.failed`. `rate_limited` không retry ngay.
- Emit event `model.fallback` (profile từ → tới). Không thêm biến môi trường mới. Cần đọc `resolver.py` để nối điểm gọi lại (route bind lúc bắt đầu run, lỗi xảy ra lúc gọi).

### 3. Flutter
- `founder_command_center_controller.dart` (handler `run.failed`): ưu tiên `payload['user_message']`, fallback chuỗi cũ.
- `direct_agent_chat_controller.dart`: truyền `conversationId` vào `streamRunEvents` (đóng lỗ hổng 404 ở chat trực tiếp).

### 4. Tool `workspace.context.read`
- `input_schema.variables` thành `oneOf` theo `operation_id`: `workspaceContext` → `{question}`; `enterpriseKnowledgeSearch` → `{query, limit?}`; mô tả tool nêu rõ.
- 422 nêu biến hợp lệ của operation đó.
- Lỗi validate đầu vào của tool trả về model dưới dạng kết quả tool lỗi để tự sửa và gọi lại, không làm run thất bại (cần đọc cách kernel xử lý tool exception hiện tại).

### 5. Ngữ cảnh phiên
- `PromptBundle` thêm `session_context`: `workspace_id`, `project_id` (+ tên, stage P0–P6 nếu có), locale; nguồn là dữ liệu backend đã verify (`verified_project`), không lấy từ client. Kèm quy tắc "không hỏi người dùng các giá trị này".
- Tool nhận `project_id` mặc định từ run context khi bỏ trống; `project_id` khác project của run → chặn (chống đọc chéo project).

### 6. Lỗi HTTP 500
- Endpoint: `listEscalations`, `getDashboardSummary`, work products, project activity, agent runs. Chưa có stack trace. Quy trình: lấy log server hoặc tái hiện bằng test (systematic-debugging), tìm nguyên nhân gốc chung, sửa. Không hứa cách sửa trước khi có bằng chứng.

## Kiểm thử
- Đơn vị: bộ phân loại lỗi; `PromptBundle` có `session_context`; default `project_id` và chặn khác project.
- Kernel: `run.failed` có `user_message`; fallback thành công / hết danh sách / không cấu hình.
- Tool: schema `oneOf`, 422 có gợi ý, lỗi tool trả về model.
- Flutter: handler lỗi dùng `user_message`; direct chat truyền `conversationId`.
- 500: test tái hiện cho từng endpoint trước khi sửa.

## Ngoài phạm vi
- Nạp tiền/cấu hình profile OpenRouter (người dùng tự làm qua Cài đặt → Model Providers).
- Refactor kernel ngoài các điểm nêu trên.
