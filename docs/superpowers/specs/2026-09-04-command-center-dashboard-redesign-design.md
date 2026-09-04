# Command Center Dashboard Redesign — Design

Ngày: 2026-09-04
Trạng thái: Approved (brainstorming), chờ writing-plans

## Bối cảnh

Founder xem screenshot Command Center (`/hub`, tab "Command Center") và đưa 3 feedback:

1. Đưa thống kê (4 số liệu) lên đầu trang.
2. "Hành động tuần đầu" cần trở thành task-list có thể edit giờ + checkbox hoàn thành, chuyển vào card bên trái.
3. Card "Hàng đợi" (queue) bên phải cần gọn hơn.

Màn hình thật: `frontend/lib/modules/hologram_hub/views/hologram_hub_view.dart`
(`HologramHubView`), state management GetX, controller
`FounderCommandCenterController`
(`frontend/lib/modules/hologram_hub/controllers/founder_command_center_controller.dart`).

Cấu trúc hiện tại của `_buildCommandCenterTab()` (dòng 397-496):
1. `CoFounderCardWidget` — banner "COSA Co-Founder" + 4 số liệu thống kê.
2. Banner "Vòng hiện tại: ... · N tuần" — chứa "Hành động tuần đầu" (chip tĩnh,
   dòng 685-717), dữ liệu từ `controller.activeProjectSetup.value.firstWeekActions`.
3. Grid 2 cột: trái = `Top3FocusWidget` (flex 6), phải = `WaitingForYouWidget`
   (flex 5, "Hàng đợi").

## Phát hiện quan trọng (đã verify bằng code)

- `FirstWeekActionDraft` (Dart model,
  `frontend/lib/data/models/project_operating_setup_model.dart:44-53`) chỉ có
  `id`/`title` — không có time/completed.
- Nhưng backend: mỗi `firstWeekAction` khi lưu (draft hoặc activate) được
  materialize 1-1 thành 1 row trong `operating.tasks`
  (`services/company/operations/strategy/services/project-kickoff-materialize.service.ts`),
  **dùng chung `id`**. Bảng `operating.tasks`
  (`services/company/shared/db/schema/operations.ts:18-42`) đã có sẵn
  `status` (`todo/in_progress/waiting_approval/blocked/done/cancelled`),
  `plannedStartAt`, `dueAt`, `updatedAt`.
- API hiện tại (`ProjectOperatingSetupView`/`toView()` trong
  `project-operating-setup.service.ts`) chỉ trả `{ id, title }` cho mỗi
  action — không trả `status`/`plannedStartAt`/`updatedAt` dù các cột này đã
  tồn tại trên chính task đó.
- `services/company/operations/handlers/task.handler.ts` đã có
  `updateTaskStatus` (`POST /operations/tasks/:id/status`) nhưng **chưa có**
  endpoint để sửa `plannedStartAt`.

→ Kết luận: không cần thêm field mới vào JSONB draft/Dart model. Chỉ cần (a)
join thêm dữ liệu từ `tasks` khi trả `firstWeekActions`, và (b) thêm 1 API
hẹp để sửa `plannedStartAt`.

## Thiết kế

### 1. Vị trí thống kê

Tách 4 số liệu (Mục tiêu đúng hạn / Missions đang chạy / Quyết định cần chốt /
Rủi ro cần lưu ý) ra khỏi `CoFounderCardWidget` thành 1 stat-bar riêng, đặt
**trên cùng** trang (trước cả banner chào "COSA Co-Founder"). Banner chào
xuống ngay dưới stat-bar. Các phần còn lại của `_buildCommandCenterTab()`
giữ nguyên thứ tự.

Phạm vi: chỉ đổi layout/thứ tự trong `hologram_hub_view.dart` +
`cofounder_card_widget.dart` (tách widget con), không đổi nguồn dữ liệu
(`CompanyPulseModel`).

### 2. Task-list "Hành động tuần đầu" → card trái

**Backend (`services/company/operations`):**

- Mở rộng `toView()`
  (`operations/strategy/services/project-operating-setup.service.ts`) để mỗi
  phần tử `firstWeekActions` trả thêm `status`, `plannedStartAt`,
  `updatedAt` — join theo `id` với bảng `operating.tasks` (chỉ đọc, không
  đổi schema `project_operating_setups`).
- Thêm endpoint mới, theo đúng pattern single-field hiện có của
  `updateTaskStatus`:
  `POST /operations/tasks/:id/schedule { plannedStartAt: string | null }`
  trong `task.handler.ts` + service tương ứng trong `task.service.ts`
  (`updateTaskScheduleService`). Validate: `plannedStartAt` là ISO date hợp
  lệ hoặc null (bỏ lịch).
- Checkbox hoàn thành dùng thẳng API có sẵn:
  `POST /operations/tasks/:id/status` với `status: "done"` (tick) /
  `"todo"` (untick).

**Frontend (Flutter):**

- `FirstWeekActionDraft`
  (`frontend/lib/data/models/project_operating_setup_model.dart`) thêm 3
  field optional: `status`, `plannedStartAt`, `updatedAt` (parse từ JSON
  response mở rộng ở trên).
- `Top3FocusWidget`
  (`frontend/lib/modules/hologram_hub/widgets/top3_focus_widget.dart`) thêm
  1 section checklist ngay dưới nội dung "Top 3 trọng tâm" hiện có. Mỗi
  item:
  - Checkbox trái — tick/untick gọi API status, optimistic update rồi
    refresh `activeProjectSetup`.
  - Title.
  - Badge giờ bên phải (hiển thị `plannedStartAt` nếu có, hoặc "Chưa đặt
    giờ") — bấm mở time-picker (`showTimePicker`/`showDatePicker` tuỳ chọn
    ngày+giờ), gọi API schedule mới khi chọn xong.
- Xoá phần render chip tĩnh "Hành động tuần đầu"
  (`hologram_hub_view.dart:685-717`) khỏi banner "Vòng hiện tại" — banner
  này giữ lại phần còn lại (tên vòng, outcome, ngày review).
- `FounderCommandCenterController`
  (`founder_command_center_controller.dart`) thêm 2 method:
  `toggleFirstWeekActionStatus(actionId)` và
  `updateFirstWeekActionSchedule(actionId, DateTime?)`, gọi service tương
  ứng, sau đó reload `activeProjectSetup`.

### 3. Hàng đợi gọn bên phải

Đổi tỉ lệ `flex` trong grid 2 cột của `_buildCommandCenterTab()`
(`hologram_hub_view.dart:435-490`) từ `Top3FocusWidget: 6 / WaitingForYouWidget: 5`
(~55/45) sang **`7/3`** (~70/30) — cột trái (Top3 + checklist mới) chiếm
phần lớn không gian, `WaitingForYouWidget` thu gọn thành sidebar hẹp hơn hẳn.
Không đổi nội dung/layout bên trong `WaitingForYouWidget` — chỉ đổi bề rộng
cột chứa nó. Layout mobile (stack dọc, `isWide == false`) giữ nguyên không
đổi.

## Ngoài phạm vi

- Không đổi cách tính/API cho 4 số liệu thống kê (`CompanyPulseModel`) — chỉ
  đổi vị trí hiển thị.
- Không thêm tính năng "task lặp lại định kỳ" (recurring task) — "vòng lặp
  task" trong feedback được hiểu là danh sách task dạng loop/checklist có
  thể edit, không phải task lặp lại theo lịch.
- Không đổi nội dung/hành vi xử lý quyết định-phê duyệt trong
  `WaitingForYouWidget`/`decision_modal_sheet.dart` — chỉ đổi bề rộng cột.

## Testing

- Backend: test mới cho `updateTaskScheduleService`/endpoint schedule (đặt
  giờ hợp lệ, giờ null để bỏ lịch, id không tồn tại → 404); test mở rộng cho
  `toView()` xác nhận `firstWeekActions` trả kèm `status`/`plannedStartAt`.
- Frontend: cập nhật `project_kickoff_controller_test.dart` (đang có sẵn,
  hiện bị sửa dở theo git status) và thêm test cho
  `toggleFirstWeekActionStatus`/`updateFirstWeekActionSchedule` trong
  `founder_command_center_controller` test; widget test cho checklist mới
  trong `Top3FocusWidget` (tick checkbox, mở time-picker).
- `make services-test-company`, `cd frontend && flutter test`, `make
  frontend-analyze`.
