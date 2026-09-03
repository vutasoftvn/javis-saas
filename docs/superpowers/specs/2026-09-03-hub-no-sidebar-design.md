# Hub không sidebar — hoàn tất migrate route + module switcher

**Ngày:** 2026-09-03
**Trạng thái:** Đã duyệt thiết kế, chờ viết plan
**Bối cảnh:** Sub-project 2/4 của đợt cải tiến UI lớn hơn (Work home — đã có
spec riêng `2026-09-03-work-overview-tab-design.md`, sidebar Hub — spec này,
kéo-thả voice→chat, rà soát OKR/12WY/Task). Xử lý tuần tự, mỗi việc 1
spec/plan riêng.

## 1. Vấn đề và bối cảnh có sẵn

Route `/hub` hiện render `DashboardView` → `AppShell` (vẽ sidebar cố định) →
`DashboardContentBody`. Khi `currentIndex == 0` ("COSA Command Center"),
`DashboardContentBody._buildFeatureView` (dòng 86-88) trả về
`const HologramHubView()` — nghĩa là **nội dung Hub không-sidebar ĐÃ TỒN TẠI
VÀ ĐANG CHẠY THẬT**, chỉ đang bị nhét vào bên trong `AppShell` nên luôn kèm
sidebar. `HologramHubView` (1080 dòng, có test riêng, cập nhật tích cực gần
đây) không phải code chết — chỉ là hiển thị sai chỗ.

Đây là hệ quả của 1 migration đang dang dở, tự documented trong chính code
(`module_routes.dart:21-32`, `dashboard_content_body.dart:21-32`, gọi là
"Task 9"): 11/21 mục sidebar đã có route canonical riêng
(`WorkspaceModule` + `moduleRoutes`, bọc trong `AppShell`), còn lại
**10 mục** vẫn sống nhờ switch-case trong `DashboardContentBody` vì "retain
feature pages initially". Cả 10 view ĐÃ tồn tại như widget riêng biệt (import
sẵn ở đầu `dashboard_content_body.dart`) — chỉ chưa có route/binding/AppShell
wrap riêng:

| Index | Module | View đã có |
|---|---|---|
| 19 | Sơ đồ tổ chức | `OrganizationView` |
| 24 | Cần bạn xử lý | `NeedsYouView` |
| 25 | Công việc tắc nghẽn | `BlockedWorkView` |
| 26 | Giám sát công việc | `WorkInspectorView` |
| 27 | OKRs | `OkrsView` |
| 28 | Kế hoạch 12WY | `TwelveWeekYearView` |
| 29 | Dự án | `ProjectRoadmapView` |
| 30 | Quản trị Template | `TemplateLibraryView` |
| 32 | Nguồn lực & Tài trợ | `ProjectFundingView` |
| 33 | Kỹ năng AI | `SkillRegistryView` |

Việc cần làm không phải "xây trang mới" — mà là **lặp lại đúng pattern của 11
module đã migrate** cho 10 module còn lại, theo đúng tinh thần đã ghi trong
code: "Switch chỉ được XOÁ HẲN khi mọi mục sidebar đều có route canonical."

## 2. Thiết kế

### 2.1 Giai đoạn 1 — Hoàn tất migrate 10 module còn lại

Với MỖI module trong bảng trên, lặp lại đúng pattern đã dùng cho 11 module
hiện có (`module_routes.dart:122-217`):

1. Thêm giá trị vào `enum WorkspaceModule` (dòng 45-58).
2. Thêm dòng vào `legacyDashboardIndexForModule` (dòng 92-104) — path tự động
   là `/work/<tên>` qua extension có sẵn (dòng 60-66), không cần sửa gì thêm
   ở đó.
3. Thêm 1 `GetPage` vào `moduleRoutes` (dòng 122-217): bọc view đã có sẵn
   bằng `AppShell(activeModule: WorkspaceModule.<tên>, child: <View>())`,
   middlewares `[AuthMiddleware(), ProjectSetupGuardMiddleware()]` (giống hệt
   11 module kia — trừ khi 1 module cụ thể có lý do rõ ràng để khác, phải nêu
   trong plan).
4. Binding: 11 module hiện có đều dùng 1 `XBinding` riêng — nhưng 10 view còn
   lại **chưa có Binding class nào** (đã kiểm tra, không tìm thấy). Cần xác
   định khi viết plan: mỗi view tự quản controller qua `Get.put`/`Get.find`
   trong `initState()` (không cần Binding mới), hay đang ngầm dựa vào
   controller mà `DashboardBinding` (binding hiện tại của `/hub`) đã đăng ký
   sẵn dạng `permanent` (nếu vậy, phải viết `XBinding` mới để route độc lập
   không bị thiếu controller). Đây là việc PHẢI kiểm tra riêng cho từng view
   trước khi viết route — không giả định chung 1 cách cho cả 10.
5. Xoá case tương ứng khỏi switch trong `DashboardContentBody`
   (`dashboard_content_body.dart:89-108`).
6. Cập nhật `DashboardNavConfig` (nếu sidebar cũ còn hiển thị các mục này
   trong giai đoạn chuyển tiếp — xem §2.2) hoặc để nguyên nếu sidebar dùng
   chung nguồn cho mọi module.

Sau khi cả 10 module xong, switch trong `DashboardContentBody` chỉ còn lại
`case 0` (và `default`) — đúng như comment trong code đã dự đoán.

### 2.2 Giai đoạn 2 — Đổi route `/hub`

Khi Giai đoạn 1 hoàn tất (switch chỉ còn case 0), sửa `GetPage` của
`AppRoutes.hub` (`app_pages.dart:94-99`) từ:

```dart
GetPage(name: AppRoutes.hub, page: () => const DashboardView(), binding: DashboardBinding(), ...)
```

thành trỏ thẳng `HologramHubView` — **không bọc `AppShell`**:

```dart
GetPage(name: AppRoutes.hub, page: () => const HologramHubView(), binding: <binding cần cho FounderCommandCenterController/DashboardController mà HologramHubView đang Get.find>, ...)
```

`DashboardView`, `DashboardContentBody`, `DashboardBinding`, và toàn bộ logic
"legacy index" (`moduleForLegacyIndex`, `legacyDashboardIndexForModule`,
`_navigateOrChangePage`, `_resolveActiveIndex` trong `dashboard_sidebar.dart`)
trở thành **dead code**, xoá trong cùng giai đoạn này (không để lại code chết
mới, đúng nguyên tắc CLAUDE.md).

Sidebar (`DashboardDesktopSidebar`/`DashboardMobileDrawer`) vẫn tiếp tục là
chrome của `AppShell` cho 21 module còn lại (Work, OKRs, 12WY, Dự án...) —
KHÔNG đổi gì ở đó. Chỉ riêng `/hub` không còn đi qua `AppShell`.

### 2.3 Giai đoạn 3 — Module switcher overlay cho Hub

Vì `HologramHubView` không có sidebar, thêm 1 icon menu ở header (bên cạnh
icon Profile hiện có, `hologram_hub_view.dart` khoảng dòng 283) mở 1
`showModalBottomSheet` liệt kê toàn bộ module — **tái dùng
`DashboardNavConfig.coreNavGroups`** làm nguồn dữ liệu (không tạo danh sách
module thứ 2 để tránh lệch đồng bộ với sidebar của các module khác), mỗi mục
điều hướng bằng `Get.toNamed(module.path)` (giờ TẤT CẢ mục đều có path canonical
thật sau Giai đoạn 1, không còn nhánh "legacy index" nào cần xử lý riêng).

## 3. Ngoài phạm vi (Non-goals)

- Không thiết kế lại nội dung của 10 view đang migrate — chuyển chỗ nguyên
  trạng, không sửa UI/logic bên trong.
- Không đổi sidebar của các module khác (Work, OKRs...) — vẫn còn sidebar,
  đúng yêu cầu gốc chỉ riêng Hub.
- Không làm ở đây: tính năng kéo-thả voice→chat (sub-project 3, spec riêng).

## 4. Rủi ro

- **Binding cho 10 view** (đã nêu ở §2.1 bước 4) là ẩn số lớn nhất — có thể
  phát hiện thêm việc khi viết plan (vd 1 view đang ngầm dựa vào state của
  `DashboardController` mà nếu tách route riêng sẽ mất).
- **`HologramHubView` cần binding gì khi đứng làm route gốc** — hiện nó dùng
  `Get.find<FounderCommandCenterController>()` và `Get.find<DashboardController>()`
  giả định đã được `DashboardBinding` đăng ký `permanent` từ trước; khi
  `DashboardBinding` bị xoá (Giai đoạn 2), phải xác định ai đăng ký các
  controller này thay thế (có thể đã có 1 chỗ khác đăng ký `permanent: true`
  qua toàn app, cần verify — nếu không, `HologramHubView` route mới cần
  binding riêng).
- Việc lớn, nên plan có thể cần tách thành nhiều lượt thực thi (vd 10 module ở
  Giai đoạn 1 chia theo agent-per-module) thay vì 1 lượt duy nhất.
