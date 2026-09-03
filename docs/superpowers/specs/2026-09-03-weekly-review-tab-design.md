# Tab "Review tuần" trong module 12WY

**Ngày:** 2026-09-03
**Trạng thái:** Đã duyệt thiết kế, chờ viết plan
**Bối cảnh:** Sub-project 4/4 (cuối) của đợt cải tiến UI lớn hơn (Work home,
sidebar Hub, icon robot/chat kéo-thả — 3 spec trước). Khảo sát ban đầu xác
nhận OKR/12WY/Task đều đã hoàn thiện (API thật, có test) — khoảng trống duy
nhất là chưa có nơi nào để chốt đánh giá tuần.

## 1. Vấn đề

Bảng `operating.weekly_plans` đã có sẵn 3 cột `executionScore`,
`outcomeScore`, `reflection` (`services/company/shared/db/schema/operations.ts`)
— thiết kế cho đúng mục đích review tuần — nhưng **không có UI nào và cũng
không có API update nào** ghi vào 3 cột này. Chỉ có
`createWeeklyPlanService`/`listWeeklyPlansService` (đọc/tạo), không có
update. Founder không có cách nào chốt review 1 tuần đã qua.

Đây chính là dữ liệu mà tính năng materialize kickoff (đã làm ở phiên trước,
xem `docs/superpowers/plans/2026-09-03-kickoff-materialize-weekly-tasks.md`)
tạo ra: mỗi project active có `twelve_week_cycles` → `weekly_plans` (tuần 1)
→ `weekly_commitments`/`tasks`. Trang này là bước tiếp theo tự nhiên: xem lại
những gì đã cam kết trong tuần và chấm điểm.

## 2. Thiết kế

### 2.1 Backend — API update còn thiếu

Thêm vào `services/company/operations/services/twelve-week-year.service.ts`:

```ts
export interface UpdateWeeklyPlanRequest {
  workspaceId: string | number;
  authorization?: string;
  executionScore?: number | null;
  outcomeScore?: number | null;
  reflection?: string | null;
}

export async function updateWeeklyPlanService(
  planId: string,
  req: UpdateWeeklyPlanRequest
): Promise<WeeklyPlan> { ... }
```

Validate: `executionScore`/`outcomeScore` trong khoảng [0, 100] (hoặc [0, 1] —
xác nhận đơn vị đang dùng ở `weekly_execution_gauge.dart` khi viết plan, phải
khớp chứ không tự chọn đơn vị mới). Xác thực quyền qua `requireWorkspaceAccess`
đúng pattern các hàm khác trong cùng file. Thêm endpoint (PATCH) trong
1 handler tương ứng (module `operations`, theo đúng layout Encore chuẩn —
handler chỉ parse/validate/gọi service, không đụng Drizzle).

### 2.2 Frontend — tab mới trong `StrategyView`

`StrategyView` (`frontend/lib/modules/strategy/views/strategy_view.dart`)
hiện có `TabBar`/`TabBarView` 6 tab (dòng 52-159), tab thứ 6 là
`TwelveWyLoopTab()`. Thêm tab thứ 7 **"Review tuần"** →
`WeeklyReviewTab` (file mới `views/tabs/weekly_review_tab.dart`).

Nội dung tab:
1. Chọn cycle/tuần đang xem (mặc định tuần hiện tại của project đang active —
   tái dùng dữ liệu `TwelveWyStateMixin` đã tải, không fetch riêng nếu đã có).
2. Danh sách `weekly_commitments` của tuần đó kèm trạng thái (done/cancelled/
   todo) — chỉ hiển thị, không sửa ở đây (sửa task thật vẫn qua module Work).
3. Form chấm điểm: 2 slider/input số cho `executionScore`/`outcomeScore`, 1 ô
   text nhiều dòng cho `reflection`. Nút "Lưu review" gọi
   `TwelveWyService.updateWeeklyPlan(planId, ...)` (thêm method mới, gọi
   endpoint ở §2.1).
4. Sau khi lưu, cập nhật lại `weekly_execution_gauge.dart` đang hiển thị ở
   Hub (đọc cùng nguồn `weekly_plans`, tự phản ánh giá trị mới — không cần
   đồng bộ thủ công nếu cả hai cùng đọc từ 1 state/service).

## 3. Ngoài phạm vi (Non-goals)

- Không tạo tuần 2, 3... mới ở đây — chỉ review tuần ĐÃ TỒN TẠI (tạo tuần mới
  là 1 tính năng riêng, chưa thiết kế).
- Không đổi cách `weekly_execution_gauge.dart` hiển thị — chỉ đảm bảo nó đọc
  đúng giá trị mới sau khi review được lưu.
- Không làm review cho OKR (OKR đã có cơ chế riêng, không liên quan
  `weekly_plans`).

## 4. Rủi ro

- Cần xác nhận đơn vị điểm số (0-100 hay 0-1) đang dùng ở
  `weekly_execution_gauge.dart` trước khi viết API — sai đơn vị sẽ làm gauge
  hiển thị sai ngay cả khi API đúng.
- 1 project có thể có nhiều `weekly_plans` (nhiều tuần) theo thời gian —
  cần xác nhận cách chọn "tuần đang xem" nhất quán với cách 12WY hiện tại xác
  định "tuần hiện tại" (`currentWeek` trên `twelve_week_cycles`), không tự
  nghĩ ra logic chọn tuần khác.
