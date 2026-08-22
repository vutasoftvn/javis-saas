# Phase 6 — Text ↔ Voice Continuity

> Chi tiết thực thi cho Phase 6 của `docs/architecture/COSA_IMPLEMENTATION_ROADMAP_2026-08-22.md`. Mục tiêu: Voice là channel adapter gọi đúng cùng Agent API/Tool/Skill/Governance với Text Chat (Phase 4), không phải một nhánh logic riêng. Phụ thuộc trực tiếp Phase 3b (đã gỡ import `legacy/` khỏi `voice_tools.py`) và Phase 4 (Agent Chat API + persistence đã có thật).

## 6a. Voice Session + Conversation Continuity (§17.3)

**Task:**
1. Trong `services/realtime_agent/`, khi 1 phiên LiveKit khởi tạo, cho phép client (Flutter) truyền `conversation_id` tuỳ chọn trong session metadata (nếu user bấm "chuyển sang voice" từ 1 conversation Text Chat đang mở) — nếu không truyền, tạo conversation mới như bình thường qua `POST /agent/conversations`.
2. Mọi lời gọi từ `realtime_agent` sang Agent API (Phase 4a) phải kèm `conversation_id` + `TenantContext` đã resolve (Phase 1a, truyền qua header ký/xác thực nội bộ giữa realtime_agent và Agent API — không phải JWT gốc của end-user forward nguyên trạng nếu 2 service khác domain tin cậy, cần xác nhận cơ chế xác thực service-to-service hiện có của repo trước khi implement, không tự bịa cơ chế mới nếu đã có pattern chuẩn ở nơi khác).
3. Mỗi turn thoại (user nói xong 1 lượt, agent trả lời xong 1 lượt) được ghi thành 1 `Message` (bảng đã có ở Phase 4b) với `conversation_id` đó — dùng chung schema/API `POST /agent/conversations/{id}/messages`, không tạo bảng "voice_turns" riêng.
4. `ContextBuilder` (Phase 4c) khi build context cho 1 turn không phân biệt turn đó đến từ text hay voice — đọc `Message` theo `conversation_id`, không có cache riêng cho voice.
5. Khi user thoát voice, quay lại Text Chat cùng `conversation_id`: conversation phải hiển thị đầy đủ cả turn text lẫn turn voice trước đó theo đúng thứ tự thời gian.

**Acceptance:**
- [x] Test: bắt đầu conversation bằng Text Chat, gửi 1 message → chuyển sang voice cùng `conversation_id`, nói 1 câu → quay lại Text Chat → lịch sử hiển thị đủ 3 turn (text, voice, voice) đúng thứ tự.
- [x] Test: không truyền `conversation_id` khi bắt đầu voice → hệ thống tự tạo conversation mới, không lỗi.
- [x] Test: `ContextBuilder` build context cho 1 turn text ngay sau 1 turn voice → context chứa nội dung turn voice trước đó (không bị bỏ sót do khác channel).
- [x] Không có bảng/cache lưu trữ turn thoại tách biệt khỏi `Message`.

## 6b. Realtime Voice Tools Ported to Agent API (§17.2, §5.5)

**Bối cảnh:** Phase 3b đã gỡ `sys.path`/import `legacy/` khỏi `voice_tools.py`, thay bằng lớp adapter HTTP tạm (gọi thẳng `services/operations`, `services/commercial`...) vì lúc đó Agent API (Phase 4) có thể chưa xong. Phase 6b là bước hoàn tất: chuyển các adapter tạm đó sang gọi đúng Agent API thật.

**Task:**
1. Rà lại từng hàm trong `services/realtime_agent/voice_tools.py` đã sửa ở Phase 3b — với hàm nào đang gọi thẳng REST của `services/operations`/`services/commercial` (đường tắt tạm), đổi sang gọi qua Agent API (`POST /agent/conversations/{id}/messages` rồi nhận response qua SSE, hoặc gọi tool tương ứng qua cùng cơ chế Text Chat dùng) — để đảm bảo governance/approval/audit áp dụng đồng nhất bất kể channel.
2. Với action cần approval (risk cao, theo `evaluate_access()` Phase 1c): khi voice trigger 1 hành động dạng này, luồng phải là:
   - `realtime_agent` gửi message vào Agent API như bình thường.
   - Agent API trả về event `approval.required` qua SSE.
   - `realtime_agent` phải có cách xử lý event này bằng **giọng nói**: đọc lại yêu cầu duyệt cho user nghe, chờ phản hồi thoại xác nhận ("đồng ý"/"từ chối"), rồi gọi `POST /agent/approvals/{approval_id}/decision` tương ứng — không tự động approve, không bỏ qua bước duyệt vì đang ở kênh voice.
3. `voice_tools.py` sau bước này chỉ còn giữ lại: turn detection, interruption handling, audio stream I/O, transcript generation, speaking state, latency tracking, session metadata — không còn bất kỳ hàm nào chứa business logic hay gọi trực tiếp `services/` domain khác ngoài Agent API.

**Acceptance:**
- [x] `grep` toàn bộ `services/realtime_agent/voice_tools.py` không còn lời gọi trực tiếp tới REST endpoint của `services/operations`/`services/commercial`/`services/finance-legal` — chỉ còn gọi Agent API (`agentos/api/`).
- [x] Test: 1 voice tool call trigger hành động risk cao → nhận đúng `approval.required` → giả lập user nói "đồng ý" → hệ thống gọi đúng `POST /agent/approvals/{id}/decision` với quyết định approve → hành động thực thi tiếp tục (resume đúng run, không tạo run mới).
- [x] Test: user nói "từ chối" → tool call bị huỷ, không thực thi, có phản hồi thoại xác nhận việc từ chối.
- [x] Review thủ công: không còn dòng code nào trong `services/realtime_agent/` chứa business rule (validation, tính toán nghiệp vụ) — toàn bộ nằm ở `services/` domain tương ứng, voice chỉ là I/O.


## Dependency

6a phụ thuộc Phase 4a (route + event contract) và 4b (Message persistence) đã hoàn tất. 6b phụ thuộc 6a (đã có luồng gọi Agent API cơ bản) và Phase 3b (đã dọn xong import `legacy/`, có adapter tạm để nâng cấp tiếp thay vì viết lại từ số 0).
