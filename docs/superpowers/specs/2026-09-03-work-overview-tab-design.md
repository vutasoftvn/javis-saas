# Tab "Tổng quan" cho module Work

**Ngày:** 2026-09-03
**Trạng thái:** Đã duyệt thiết kế, chờ viết plan
**Bối cảnh:** Đây là sub-project 1/4 trong 1 đợt cải tiến UI/UX lớn hơn (Work home,
sidebar Hub, kéo-thả voice→chat, rà soát OKR/12WY/Task) — 4 việc độc lập, xử lý
tuần tự, mỗi việc 1 spec/plan riêng. Sub-project 2 (sidebar Hub) sẽ brainstorm
tiếp sau khi spec này được duyệt.

## 1. Vấn đề

Module Work (`frontend/lib/modules/tasks/`) hiện chỉ có 1 màn hình: bảng Kanban 5
cột (`tasks_view.dart:22-104`). Không có nơi nào tổng hợp: việc cần làm hôm nay,
thống kê tiến độ, thông tin quản trị project đang chạy, hay liên kết nhanh sang
OKR/12WY. Founder phải tự suy luận từ Kanban thô.

## 2. Thiết kế

### 2.1 Cấu trúc

`TasksView` đổi từ 1 màn hình đơn thành `TabBarView` 2 tab:

1. **"Tổng quan"** (mới) — nội dung mô tả ở §2.2.
2. **"Kanban"** — y nguyên nội dung hiện tại của `TasksView`, tách thành widget
   con `TaskKanbanTab` (đổi tên/di chuyển thuần tuý, không đổi logic).

Không tạo module `work` riêng — giữ trong `lib/modules/tasks/` theo đúng cấu
trúc thư mục đang có (`views/`, `controllers/`, `views/tabs/` mới cho 2 tab).

### 2.2 Nội dung tab "Tổng quan" (4 khối, theo đúng lựa chọn đã chốt)

1. **Việc hôm nay** — danh sách task có `dueAt` = hôm nay hoặc đã quá hạn và
   chưa `done`/`cancelled`, sắp theo `dueAt` tăng dần, bấm vào mở task đó
   (dùng lại cơ chế mở task chi tiết đã có ở Kanban, không xây mới).
2. **Thống kê task theo trạng thái** — đếm số task theo 5 trạng thái Kanban
   (`todo`/`in_progress`/`waiting_approval`/`blocked`/`done`), hiển thị dạng
   thẻ số + màu theo đúng bảng màu Kanban hiện có (không tạo bảng màu mới).
3. **Thông tin quản trị project đang chọn** — 1 dropdown chọn project (dữ liệu
   lấy từ danh sách project đã tải sẵn ở tầng dashboard/FCC, không fetch lại),
   hiển thị: `selectedStage` (P0-P6), `status` operating setup
   (NOT_STARTED/IN_PROGRESS/ACTIVE), `stageTargetDate`, tên người phụ trách
   nếu có. Nguồn: `ProjectOperatingSetupService.get(projectId)` (đã tồn tại).
4. **OKR + 12WY rút gọn** — 1 thẻ nhỏ: % hoàn thành OKR chu kỳ hiện tại (từ
   `OkrService`) và điểm thực thi tuần hiện tại của 12WY (từ `TwelveWyService`,
   tái dùng đúng field đang hiển thị ở `weekly_execution_gauge.dart`). Bấm vào
   mỗi thẻ điều hướng sang trang OKR/12WY đầy đủ tương ứng (dùng route đã có).

### 2.3 Nguồn dữ liệu — không gọi API thừa

- Khối 1 + 2: tính hoàn toàn từ danh sách task mà `TasksController` **đã tải
  sẵn** cho Kanban (cùng 1 controller/instance, dùng `Obx` đọc chung
  `tasks` RxList) — không fetch riêng, không tạo request thứ 2 cho cùng dữ
  liệu.
- Khối 3 + 4: gọi song song bằng `Future.wait` khi tab "Tổng quan" được mở lần
  đầu (hoặc khi đổi project ở dropdown) — dùng đúng service methods hiện có
  (`ProjectOperatingSetupService`, `OkrService`, `TwelveWyService`), không tạo
  endpoint backend mới.

### 2.4 Trạng thái loading/error

Theo đúng pattern Rx đang dùng toàn app: mỗi khối có `isLoading`/`errorMessage`
riêng (không block cả tab nếu 1 khối lỗi — vd OKR service lỗi vẫn hiển thị được
khối "Việc hôm nay" bình thường).

## 3. Ngoài phạm vi (Non-goals)

- Không tạo endpoint backend aggregate mới.
- Không đổi logic/API của Kanban hiện có — chỉ di chuyển UI vào 1 tab con.
- Không xây báo cáo dạng biểu đồ phức tạp (chart library) — thẻ số + list là đủ
  cho bản đầu; nếu sau này cần biểu đồ thật, đó là 1 spec riêng (và phải qua
  skill `dataviz` khi tới lúc).
- Không đổi cách chọn/quản lý project ở nơi khác trong app — dropdown ở đây chỉ
  đọc danh sách có sẵn, không tạo luồng tạo/sửa project mới.

## 4. Rủi ro

- Danh sách project dùng để đổ vào dropdown hiện nằm ở 1 vài controller khác
  nhau tuỳ ngữ cảnh (`FounderCommandCenterController.projectsList`,
  `StrategyController`) — cần xác định đúng 1 nguồn khi viết plan, tránh tạo
  thêm 1 bản fetch project thứ 3.
- `TasksController` hiện có thể không tải TOÀN BỘ task (có phân trang/giới hạn)
  — nếu vậy, khối "Việc hôm nay" tính từ danh sách chưa đầy đủ sẽ sai; cần xác
  nhận khi viết plan trước khi tin vào giả định "tái dùng dữ liệu đã tải".
