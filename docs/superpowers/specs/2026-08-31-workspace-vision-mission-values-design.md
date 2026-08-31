# Workspace Vision / Mission / Core Values — bắt buộc thiết lập

Ngày: 2026-08-31
Trạng thái: Approved (chờ implementation plan)

## Bối cảnh

Yêu cầu founder: khi tạo workspace mới phải yêu cầu nhập Vision / Mission /
Core Values; nếu đăng nhập vào một workspace đã tồn tại mà chưa có 3 trường
này thì cũng phải yêu cầu — chặn cứng, không cho vào Command Center tới khi
điền xong.

Khảo sát codebase xác nhận: hiện **không có** khái niệm Company
Vision/Mission/Values ở cấp workspace. Trường `vision_statement` trong
`twelve_week_cycles` và `mission` trong `weekly_plans`
(`services/company/shared/db/schema/operations.ts`) là của chu kỳ lập kế
hoạch 12-tuần, không phải company identity — không tái dùng được, đây là
tính năng mới.

Đây là điểm gắn tự nhiên với tính năng chat vừa được sửa trong cùng phiên
làm việc: `FounderCommandCenterController` giờ đã dùng đúng flow
`AgentChatService` (conversation → message → SSE), nên nút "Nhờ AI soạn"
trong tính năng này tái dùng lại đúng service đó thay vì tạo integration
AI mới.

## Phạm vi dữ liệu

Một bộ Vision/Mission/Core Values **cho mỗi Workspace** (không phải theo
từng Project). Đây là "company identity" cấp cao nhất, áp dụng cho toàn bộ
workspace.

## Data model

Thêm 3 cột nullable vào bảng `core.workspaces`
(`identityWorkspaces` trong `services/company/shared/db/schema/identity.ts`):

```ts
vision: text("vision"),
mission: text("mission"),
coreValues: text("core_values"),
```

Không tạo bảng con — quan hệ 1-1 với workspace, thêm cột trực tiếp khớp
pattern hiện có của bảng này (đã trộn nhiều workspace-scoped metadata khác
trong cùng bảng, ví dụ `lifecycleStage`, `runtimeMode`).

Migration mới trong `services/company/identity/migrations/` (up/down), chạy
qua `make services-migrate-company`.

`coreValues` là **một ô text nhiều dòng tự do** (không phải danh sách
chips/tags có cấu trúc) — khớp với cách `vision`/`mission` cũng là free
text, đơn giản nhất, không cần bảng con hay JSON array.

## Backend (`services/company/identity`)

### Mở rộng `GET /identity/workspaces/:id` (đã có, `expose: true`)

`Workspace` response type (`workspace.service.ts`) thêm 3 field nullable:
`vision`, `mission`, `coreValues`. Đây là cách frontend kiểm tra "đã thiết
lập company identity chưa" — không cần endpoint riêng để check.

### Endpoint mới: `PATCH /identity/workspaces/:id/company-identity`

- `expose: true`, cùng module `identity.handler.ts`/`workspace.handler.ts`.
- Input: `{ vision: string, mission: string, coreValues: string }`.
- Validate: cả 3 trường sau khi `.trim()` đều không rỗng → nếu thiếu trả
  `APIError.invalidArgument`.
- Auth: dùng `requireWorkspaceAccess(authorization, workspaceId)` — cùng
  pattern `services/company/operations/handlers/project.handler.ts` đang
  dùng — chặn workspace khác ghi đè bằng cách đoán `:id`.
- Update record, trả về `Workspace` đã cập nhật (đủ field như GET).

## Frontend

### Widget dùng chung: `CompanyIdentityModal`

Đường dẫn đề xuất:
`frontend/lib/modules/onboarding/widgets/company_identity_modal.dart` (dùng
chung cho cả luồng onboarding lẫn gate sau đăng nhập — không nhân bản UI).

- `barrierDismissible: false`, không có nút đóng/back — chặn cứng đúng yêu
  cầu founder.
- 3 ô `TextField` multiline: Vision / Mission / Core Values.
- Nút **"Nhờ AI soạn"**:
  - Tạo/mở 1 `ChatConversation` qua `AgentChatService.createConversation`
    (title `Company Identity Draft`, `activeAgentProfile: 'strategy'`).
  - Gửi 1 message với `dataAccess: BUSINESS_CONFIDENTIAL` (giống pattern đã
    dùng ở `FounderCommandCenterController`), nội dung prompt yêu cầu AI trả
    lời đúng định dạng 3 khối:
    ```
    VISION: <...>
    MISSION: <...>
    VALUES: <...>
    ```
  - Subscribe `streamRunEvents`, gom `message.delta` tới khi `run.completed`.
  - Regex tách 3 khối theo prefix `VISION:`/`MISSION:`/`VALUES:`, điền sẵn
    vào form (founder vẫn sửa được trước khi lưu).
  - Nếu regex không khớp (AI trả lời không đúng định dạng): đổ nguyên văn
    câu trả lời vào ô Vision kèm placeholder note, không chặn luồng, founder
    tự cắt dán thủ công.
- Nút **"Lưu"**: disable tới khi cả 3 ô non-empty sau `.trim()` → gọi
  `WorkspaceService.updateCompanyIdentity(workspaceId, vision, mission,
  coreValues)` (method mới, POST/PATCH qua `ApiClient.patch`) → cập nhật
  cache workspace local → đóng modal.

### Điểm gắn gate (một điểm duy nhất)

Trong `HubAuthMixin.ensureAuthenticated()`
(`frontend/lib/modules/hologram_hub/controllers/mixins/hub_auth_mixin.dart`):
sau bước xác thực user hiện có (`authService.getMe()`), gọi
`GET /identity/workspaces/:id` cho workspace hiện tại; nếu `vision` /
`mission` / `coreValues` có trường nào rỗng/null → hiện
`CompanyIdentityModal` (chặn) trước khi cho phép Hub render nội dung thật.

Điểm gắn này bắt cả 2 tình huống nêu trong yêu cầu bằng một logic duy nhất:
- Workspace vừa tạo ở Venture Onboarding (luôn thiếu 3 trường → modal hiện
  ngay khi vào Hub lần đầu).
- Workspace cũ đăng nhập lại mà chưa từng điền.

Không cần sửa riêng `VentureOnboardingScreen` — giữ nguyên luồng tạo
workspace hiện tại, tránh 2 nơi phải đồng bộ logic.

## Testing

- Backend: test mới trong `services/company/identity/tests/workspace.test.ts`
  — validate 400 khi thiếu field, 200 + persist đúng khi đủ field, 403/không
  cho phép workspace khác ghi đè qua `requireWorkspaceAccess`.
- Frontend:
  - Test cho `HubAuthMixin`/`HologramHubController`: gate hiện khi thiếu dữ
    liệu, không hiện khi đủ (mock `GET /identity/workspaces/:id`).
  - Test cho `CompanyIdentityModal`/service: nút Lưu gọi đúng PATCH endpoint
    với payload đúng; nút "Nhờ AI soạn" parse đúng 3 khối từ SSE mock (dùng
    lại pattern `MockClient` + SSE text đã viết ở
    `test/founder_command_center_chat_test.dart`); fallback khi AI trả lời
    sai định dạng.

## Ngoài phạm vi

- Không cho phép sửa Vision/Mission/Values sau khi đã lưu lần đầu (không có
  yêu cầu — nếu cần, đây là follow-up riêng, có thể thêm nút "Chỉnh sửa" ở
  màn cài đặt workspace sau).
- Không làm UI dạng chips/tags có cấu trúc cho Core Values.
- Không đổi luồng tạo workspace ở `VentureOnboardingScreen`/control-plane
  `/platform/auth/register`.
