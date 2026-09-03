# Zero-Project Setup Redirect — Design Specification

**Status:** Proposed — awaiting review
**Ngày:** 2026-09-03
**Liên quan:** [`2026-09-01-founder-project-kickoff-design.md`](2026-09-01-founder-project-kickoff-design.md) (luồng kickoff 3 bước và `ProjectOperatingSetup` mà spec này dựa lên).

## Mục tiêu

Khi workspace chưa có project nào, đưa Founder vào thẳng luồng **tạo project + kickoff**, không hiển thị Hub vận hành với các số liệu giả (`0/0 mục tiêu`, `P1`, `Missions đang chạy`, `Top 3`, nhãn `12-Week Year`).

## Vấn đề hiện tại

Sau đăng ký/đăng nhập, `auth_controller` luôn `Get.offAllNamed(AppRoutes.hub)`. Bước 2 đăng ký **bắt buộc** tạo/tham gia company, nên Founder luôn có workspace nhưng **không có project**. Hub (`HologramHubView` trong `DashboardView`) khi `hasProjects == false`:

- Vẫn render `CoFounderCardWidget` (pulse), `Top3FocusWidget`, `WaitingForYouWidget` **vô điều kiện** — chỉ chèn thêm `_buildFirstProjectBanner`.
- Các widget này hiển thị `0/0`, `P1`, `12-Week Year` như thể hệ thống đã có kế hoạch, trong khi chưa có dữ liệu nào.

Lối tạo project đầu tiên hiện tại: banner → `_showCreateProjectDialog` → `createFirstProject()` → `DashboardController.openProjectKickoff(projectId)` → set `activeKickoffProjectId` → kickoff render **lồng trong** strategy roadmap tab ([`project_roadmap_tab.dart`](../../../frontend/lib/modules/strategy/views/tabs/project_roadmap_tab.dart)). Không có route riêng, không guard, dễ bị bỏ qua.

## Quyết định trải nghiệm

**Khi workspace có 0 project (hoặc có project nhưng `operating_setup` chưa `ACTIVE`), mọi điều hướng vào `/hub` và `/work/*` bị redirect sang route tạo project `/projects/new`. Hub chỉ hiển thị lại khi đã có ít nhất một project với setup `ACTIVE`.**

## Route

`AppRoutes.projectsNew = '/projects/new'` — tên generic, **mode-aware**, dùng lại được cho project thứ 2, 3.

- Full-screen, **không dùng `AppShell`** (không sidebar module, không chat dock, không floating voice). Dùng scaffold tối giản riêng.
- Middleware: `AuthMiddleware` (đã đăng nhập local + có workspace active). Không thêm guard zero-project lên chính route này (tránh vòng lặp redirect).
- Tuỳ chọn query `?onboarding=1` chỉ để làm rõ ý định khi đọc URL; hành vi thực tế do controller quyết theo `projectCount` (xem dưới), không phụ thuộc param.

### Khác biệt "project đầu" vs "project thứ N"

Cùng một `ProjectSetupView`; khác nhau ở hành vi, do `projectCount` quyết định:

| | Project đầu (`projectCount == 0`) | Project thứ N (`projectCount >= 1`) |
|---|---|---|
| Vào bằng | Guard tự redirect (bắt buộc) | Nút "Tạo dự án mới" (tự nguyện) |
| Nút Huỷ / back | Ẩn — không thoát được khi chưa có project | Hiện — huỷ quay lại `/hub` |
| Sau khi `activate` | `Get.offAllNamed(AppRoutes.hub)` | `Get.offAllNamed(AppRoutes.hub)` (Guided Hub theo project là phạm vi spec kickoff, không phải spec này) |
| Logout | Luôn khả dụng | Luôn khả dụng |

## Cơ chế redirect (guard)

Theo đúng pattern đã có `DashboardController._ensureWorkspaceCached()` — async check trong `onInit`, `Get.offAllNamed` khi không hợp lệ.

### Điều kiện redirect

Định nghĩa `needsProjectSetup` = đúng khi **cả hai**:

1. `projectsError == null` (tải danh sách project thành công), **và**
2. `projectsList.isEmpty` **hoặc** không có project nào với `operating_setup.status == ACTIVE`.

Khi `needsProjectSetup == true` và route đích không phải `/projects/new` → `Get.offAllNamed(AppRoutes.projectsNew)`.

### Các điểm đặt guard

- `DashboardController.onInit` (route `/hub`): sau khi verify token, gọi check `needsProjectSetup`; nếu true → redirect.
- `SessionController.activateWorkspace` thành công (đổi workspace): sau khi commit context, check `needsProjectSetup` cho workspace mới; nếu true → redirect `/projects/new` thay vì `/hub`.
- Route `/work/*` (`moduleRoutes`): thêm `ProjectSetupGuardMiddleware` vào danh sách `middlewares` mỗi `GetPage` — deep-link `/work/tasks` khi 0 project cũng bị đẩy về `/projects/new`.

### Không redirect khi lỗi tải

Nếu `projectsError != null` (lỗi mạng/backend khi list projects), **không** redirect — giữ đúng logic hiện tại `hasProjects = projects.isNotEmpty || projectsError.value != null`, tránh nhốt Founder ngoài app vì lỗi tạm thời. Hub tự xử lý hiển thị trạng thái lỗi như hiện nay.

### Nguồn dữ liệu project count

`FounderCommandCenterController` đã có `projectsList`, `projectsError`, `hasProjects`, `activeProjectSetup`. Bổ sung một getter thuần `bool get needsProjectSetup` trên controller này (hoặc một service dùng chung nếu guard `/work/*` không tiện phụ thuộc `FounderCommandCenterController`). Guard chờ `loadDashboardData()` hoàn tất trước khi quyết định; trong lúc chờ hiển thị loading, không render nội dung hub.

## Màn setup (`ProjectSetupView`)

State machine, không dùng `AppShell`:

1. **Form tạo project**: `title` (bắt buộc) + `description` ngắn (tuỳ chọn). Không có dropdown P-stage (theo spec kickoff). Submit → `StrategyService.createBasicProject(title, description)` — backend luôn tạo `lifecycleStage = P0_DISCOVERY`.
2. Ngay sau khi tạo thành công → render `ProjectKickoffView(projectId: created.id)` **inline** trong cùng màn (tái dùng widget hiện có, 3 bước: Hiểu dự án → Chọn stage/timebox → Chốt tuần đầu).
3. Sau khi Founder `Xác nhận vòng đầu` (`POST /operations/projects/:id/operating-setup/activate`) → điều hướng theo bảng "Khác biệt" ở trên.
4. **Resume**: nếu vào `/projects/new` khi đã có project với `operating_setup.status != ACTIVE` (Founder tạo project rồi thoát giữa chừng) → bỏ qua bước 1, vào thẳng `ProjectKickoffView(projectId)` của project đó, resume đúng step (step do `ProjectKickoffController` xác định từ dữ liệu `operating_setup` đã persist, không thuộc spec này).

`createBasicProject` giữ nguyên; `activate` transaction giữ nguyên theo spec kickoff (validate access/workspace, P0→P1 canonical khi Founder chọn P1, persist setup/action/review cadence, emit audit/outbox — không tạo inferred goals/missions/metrics).

## Dọn Hub (lưới an toàn)

Guard là cơ chế chính; hub gần như không bao giờ render ở trạng thái 0 project nữa. Dọn thêm để phòng race / guard bị bypass:

- Bọc `CoFounderCardWidget`, `Top3FocusWidget`, `WaitingForYouWidget` trong điều kiện `controller.hasProjects.value == true`.
- Xoá `_buildFirstProjectBanner` và nhánh gọi nó (đã chết vì guard).
- `_buildSetupIncompleteCard` / `_buildActiveOperatingSetupCard` giữ nguyên (áp dụng khi đã có project).

Không đụng nội dung/visual của các widget này — chỉ thêm điều kiện render.

## Auth flow

Giữ `Get.offAllNamed(AppRoutes.hub)` trong `auth_controller` (`login` nhánh single-workspace và `submitCompanyStep`) làm **một điểm đích duy nhất** sau auth; guard tại `/hub` chịu trách nhiệm bounce sang `/projects/new`.

**Tối ưu (nice-to-have, không bắt buộc trong phạm vi này):** `syncFromPlatform` trả kèm project count để `auth_controller` điều hướng thẳng `/projects/new`, tránh nháy hub một khung hình.

## Không thuộc phạm vi

- **Spec A** (hoàn tất Task 9: cấp route `/work/*` cho ~10 mục legacy, xoá switch index trong `DashboardContentBody`, repoint alias `/dashboard` → `/work/<default>`, nhãn sidebar Hub vs Dashboard).
- **Spec C** (dockable chat panel + phiên hội thoại dùng chung xuyên `/hub` và `/work/*`).
- **Follow-up:** thay `_showCreateProjectDialog` + kickoff-lồng-trong-strategy bằng cùng route `/projects/new`, để mọi lối tạo project đi qua một chỗ. Xếp vào spec A hoặc task riêng.
- Guided Hub theo project sau `activate` (thuộc spec kickoff).
- Backend: không thay đổi API. Dùng nguyên `createBasicProject`, `GET/PUT /operations/projects/:id/operating-setup`, `POST .../operating-setup/activate`.
- Nhập project đã vận hành ("Nhập project đang vận hành") — entry riêng, không thuộc luồng này.

## Tiêu chí nghiệm thu

1. Đăng ký/đăng nhập với workspace 0 project → kết thúc ở `/projects/new`, không thấy hub với pulse/Top 3/`P1`/`12-Week Year`.
2. `projectCount >= 1` và có project `operating_setup` `ACTIVE` → vào `/hub` bình thường, không redirect.
3. Lỗi tải danh sách project (`projectsError != null`) → **không** redirect; hub hiển thị trạng thái lỗi hiện có.
4. Tạo project ở `/projects/new` rồi thoát giữa chừng, vào lại → resume đúng bước kickoff, không hiện lại form tạo project.
5. Đổi workspace sang workspace khác có 0 project → redirect `/projects/new`.
6. Deep-link `/work/tasks` khi 0 project → redirect `/projects/new`.
7. Sau `Xác nhận vòng đầu` → vào `/hub`, không bị guard đẩy lại `/projects/new`.
8. Ở `/projects/new` chế độ onboarding (`projectCount == 0`): không có nút Huỷ/back; Logout hoạt động.
9. Ở `/projects/new` chế độ thường (`projectCount >= 1`): có nút Huỷ → quay lại `/hub`.
10. Test cover: create→redirect, no-redirect khi count≥1, no-redirect khi lỗi tải, resume, đổi workspace, deep-link `/work/*`, post-activate không loop, ẩn/hiện nút Huỷ theo mode, logout từ `/projects/new`.
