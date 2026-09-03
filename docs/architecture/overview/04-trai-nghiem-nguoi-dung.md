# Trải nghiệm người dùng — Flutter & Voice

> Bối cảnh nghiệp vụ xem mục 7 trong
> [02-workflow-nghiep-vu.md](02-workflow-nghiep-vu.md). Cấu trúc thư mục
> frontend xem mục 1 trong
> [01-bon-vung-kien-truc.md](01-bon-vung-kien-truc.md).

## Module & màn hình

Frontend Flutter (`frontend/lib/modules/`) có 25 module nghiệp vụ, tổng
khoảng 46 màn hình. Các module chính người dùng chạm vào hằng ngày: `chat`,
`dashboard`, `mission_control`, `approvals`, `tasks`, `workflows`, `finance`,
`sales`, `strategy`, `vault`, `workforce`, `settings`, `onboarding`,
`workspace_picker`. Một số module ít dùng hơn hoặc mới thêm: `academy`,
`hologram_hub`, `legal`, `remote_access`, `skills`.

**Di trú `features/` vs `modules/` đang dở dang** — xem
[05-khuyen-nghi.md](05-khuyen-nghi.md#nhom-b); khi tìm code của một tính
năng, kiểm tra cả 2 thư mục nếu tên trùng (`settings`, `strategy`, `vault`,
`workforce`, `workspace_runtime`).

## Kết nối tới backend

Toàn bộ lời gọi backend đi qua lớp `MvpEndpoint`
(`frontend/lib/core/network/mvp_request_client.dart` +
`mvp_endpoints.g.dart`), đối chiếu với `shared/contracts/mvp-surface.json`
(65 capability). Các service Dart tiêu biểu dùng lớp này:
`settings_mvp_service.dart`, `workforce_mvp_service.dart`,
`workspace_runtime_mvp_client.dart`, `marketing_mvp_service.dart`,
`approvals_service.dart`, `strategy_mvp_client.dart`. Đây là cơ chế ràng
buộc bắt buộc theo `CLAUDE.md`: route lệch khỏi `mvp-surface.json` (route đã
xoá quay lại lặng lẽ, hoặc route gọi thẳng bằng string tay) sẽ bị
`make frontend-api-contract-check` chặn.

## Kiến trúc voice — cần đọc kỹ trước khi giả định

Có **3 cơ chế khác nhau** dễ bị nhầm là một:

1. **Push-to-talk (ghi âm rồi chuyển văn bản)** —
   `frontend/lib/core/services/voice_service.dart`: ghi âm ra file
   (package `record`), sau đó gọi transcribe. **Chưa chạy trên web** (có
   comment tường minh trong code: push-to-talk MVP nhắm mobile/desktop
   trước, web là việc sau, không giả vờ đã có).
2. **Kênh SSE realtime** — `frontend/lib/core/network/realtime_service.dart`
   là bộ phân tích frame Server-Sent Events cho **văn bản streaming**,
   không phải audio.
3. **Voice thời gian thực qua LiveKit — có 2 worker song song, không phải
   1** — đây là điểm dễ hiểu nhầm nhất, đã xác minh trực tiếp trong
   `docker-compose.yml`:
   - `livekit` — LiveKit server tự lưu trữ (self-hosted), chạy trong chính
     docker-compose (`livekit:7880`).
   - `realtime-agent` — worker Python (`services/realtime_agent`) đăng ký
     vào LiveKit **local** (`LIVEKIT_LOCAL_URL=ws://livekit:7880`), phục vụ
     phòng thoại tạo trên desktop.
   - `realtime-agent-cloud` — cùng image, nhưng chạy với
     `LIVEKIT_FORCE_CLOUD=true`, đăng ký vào LiveKit **Cloud**
     (`LIVEKIT_URL`), phục vụ phòng thoại tạo trên mobile/web.

   Lý do cần cả 2 (nguyên văn comment trong `docker-compose.yml`, dòng
   350-358): một worker chỉ nhận được dispatch từ đúng server LiveKit mà nó
   đăng ký — chạy thêm bản sao thứ hai của `realtime-agent` mà không ép
   cloud sẽ chỉ đăng ký lại vào local, không tự động phủ được cả 2 loại
   thiết bị. Vì vậy cả hai container phải chạy đồng thời để voice hoạt động
   đúng trên cả desktop (local) lẫn mobile/web (cloud).

   Luồng dữ liệu: Flutter (LiveKit client) → LiveKit (local hoặc cloud tuỳ
   loại thiết bị) → worker `realtime-agent`/`realtime-agent-cloud` tương ứng
   → Gemini Live.

**Lưu ý về tài liệu lệch:** `services/realtime_agent/README.md` ghi
"LiveKit (Cloud today; Local later, see DEPLOYMENT.md)" và còn nhắc tới
`backend/app`/`brain-api` — cả hai chi tiết này đã **lỗi thời so với
`docker-compose.yml` hiện tại** (worker local đã chạy thật, nghiệp vụ đã
chuyển sang `apps/cosa`). Khi có mâu thuẫn giữa README và
`docker-compose.yml`, ưu tiên tin `docker-compose.yml` vì đó là cấu hình
thực sự chạy. Xem đề xuất cập nhật README ở
[05-khuyen-nghi.md](05-khuyen-nghi.md#nhom-c).

**`desktop_worker/` không phải voice worker.** Đây là một daemon FastAPI
riêng ("COSA Local Desktop Worker Plane") chạy trên `127.0.0.1`, cung cấp
các endpoint có kiểm soát để thực thi hành động cục bộ trên máy người dùng:
`git.status/diff/read_file`, `fs.read`/`fs.write_scoped` (giới hạn theo danh
sách thư mục cho phép), `browser.open` (chỉ http/https), và
`shell.exec_sandboxed` (mặc định tắt, cần approval token, chỉ nhận
argv-list chứ không nhận chuỗi lệnh tự do). Cơ chế bảo mật gồm session token
(`~/.cosa/desktop_worker.token`) + chống replay bằng nonce. Đây từng thay
thế một endpoint `/execute-task` cũ dùng `shell=True` không xác thực — một
đợt vá bảo mật, không liên quan gì tới voice.

**Tóm lại kiến trúc voice thực tế hôm nay:**

```text
Flutter (push-to-talk, mobile/desktop, chưa có web)
   → ghi âm → transcribe (không phải luồng realtime)

Flutter (LiveKit client, thiết bị desktop)
   → LiveKit local (docker-compose: livekit:7880)
   → worker "realtime-agent" (services/realtime_agent, đăng ký local)
   → Gemini Live

Flutter (LiveKit client, thiết bị mobile/web)
   → LiveKit Cloud
   → worker "realtime-agent-cloud" (cùng codebase, LIVEKIT_FORCE_CLOUD=true)
   → Gemini Live

desktop_worker/  ── daemon khác hẳn, thực thi capability cục bộ (git/fs/shell),
                     KHÔNG xử lý voice, KHÔNG phải "realtime-agent" ở trên
```

Hai worker (`realtime-agent` và `realtime-agent-cloud`) phải chạy đồng thời
— tắt một trong hai nghĩa là một loại thiết bị (desktop hoặc mobile/web) mất
voice.
