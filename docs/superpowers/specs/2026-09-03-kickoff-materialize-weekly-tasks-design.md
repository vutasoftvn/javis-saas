# Materialize Project Kickoff "First Week" vào Weekly Plan + Tasks thật

**Ngày:** 2026-09-03
**Trạng thái:** Chờ user review
**Liên quan:** `docs/superpowers/specs/2026-09-01-founder-project-kickoff-design.md` (spec gốc của luồng kickoff — spec này KHÔNG phủ định spec gốc, chỉ bổ sung phần "chuyển draft thành dữ liệu thực thi" mà spec gốc chủ động để ngoài scope)

## 1. Vấn đề

Luồng "Thiết lập dự án" (Project Kickoff, `frontend/lib/modules/strategy/`) ở Bước 3 thu thập:
- `firstWeekOutcome` — mục tiêu định tính cho tuần đầu ("Kết quả của tuần 1")
- `firstWeekActions` — 1-3 việc cần làm trong tuần đầu

Cả hai hiện chỉ được ghi vào 2 cột (`first_week_outcome` text, `first_week_actions` jsonb) của bảng `strategy.project_operating_setups` (`services/company/shared/db/schema/strategy.ts:277-294`). Đây là **draft rời rạc, không liên kết với bất kỳ bảng thực thi nào khác** — không phải OKR, không phải task, không phải weekly plan. Founder gõ xong 3 việc thì chúng chỉ nằm im trong 1 cột JSON, không xuất hiện ở "Nhiệm vụ" (Tasks module) hay "Kế hoạch 12WY".

Đây là quyết định có chủ đích ban đầu (spec 2026-09-01, dòng 103/158 — "không tự tạo task/mission/OKR"), nhưng qua phân tích lại schema thật, kết luận: **có tồn tại sẵn 1 chuỗi thực thể "weekly, không cần OKR" đúng nghĩa** mà spec gốc chưa dùng tới — nên khoảng trống này nên được lấp bằng cách nối vào chuỗi có sẵn đó, thay vì tiếp tục để `first_week_actions` là dữ liệu chết.

## 2. Bằng chứng từ schema (đã verify trực tiếp trong code, không suy diễn)

Chuỗi thực thể liên quan (`services/company/shared/db/schema/operations.ts`):

```
strategy.projects (đã có)
      │  projectId (FK mới, xuyên schema — pattern đã có sẵn: tasks.initiativeId → strategy.initiatives.id)
      ▼
operating.twelve_week_cycles   — projectId, durationWeeks (KHÔNG bắt buộc đúng 12 tuần, chỉ là tên bảng)
      │  cycleId
      ▼
operating.weekly_plans         — weekNo, focus/mission (= MỤC TIÊU TUẦN), executionScore/outcomeScore/reflection (= REVIEW TUẦN)
      │  weeklyPlanId
      ▼
operating.weekly_commitments   — title, initiativeId (NULLABLE — xác nhận không bắt buộc OKR), status
      │  weeklyCommitmentId (tasks.weeklyCommitmentId, hiện KHÔNG có FK constraint — sẽ thêm)
      ▼
operating.tasks                — title, status, ... (xuất hiện ở module "Nhiệm vụ")
      │  taskId + projectId
      ▼
operating.task_projects        — join table, để Tasks module lọc theo project
```

Đã loại các phương án sai trong quá trình phân tích:
- `strategy.okr_cycles`/`okr_objectives`/`key_results` — bắt buộc `metricId`/`targetValue` (đo lường được), "Kết quả tuần 1" là câu mô tả định tính, không khớp.
- `strategy.weekly_reviews` — không có `project_id` (chỉ `workspace_id`), là báo cáo điều hành toàn workspace (cash/obligations), không phải review tiến độ 1 project.
- Gộp schema `operating` vào `strategy` — không cần thiết, FK xuyên schema đã là pattern có sẵn (`tasks.initiativeId → strategy.initiatives.id`).

## 3. Thiết kế

### 3.1 Nguyên tắc

- **Không đụng OKR.** `weekly_commitments.initiativeId` và không tạo `initiatives` row nào — giữ đúng tinh thần "không tự suy diễn OKR" của spec gốc, nhưng vẫn có nơi chứa "mục tiêu tuần" thật (`weekly_plans.focus`).
- **Materialize ngay khi có thay đổi**, không đợi tới activate — khớp với hành vi hiện tại (từ đợt fix trước): `addAction`/`removeAction` gọi `saveDraft` ngay lập tức. `saveDraft` và `activate` dùng chung 1 helper materialize, để không có 2 đường logic lệch nhau.
- **Diff theo `id` ổn định của action**, không theo index. Backend đã gán `id` (snowflake) cho mỗi action từ `normalizeFirstWeekActions()` (dòng 98-109) — tái dùng chính `id` này làm `tasks.id` luôn (snowflake unique toàn hệ thống, không cần thêm cột `taskId` hay bảng mapping).
- **1 cycle + 1 weekly_plan (tuần 1) cho mỗi project**, tạo lười (lazy) lần đầu có action, tái dùng cho các lần save sau (tìm theo `projectId` / `cycleId+weekNo=1`, không tạo trùng).

### 3.2 Luồng `saveProjectOperatingSetup` (và `activateProjectOperatingSetup`) sau khi sửa

Thêm bước, chạy trong cùng transaction với việc upsert `project_operating_setups`:

1. Nếu `actions` (sau normalize) rỗng → bỏ qua toàn bộ bước dưới (không tạo cycle/plan nếu chưa có action nào).
2. Tìm `twelve_week_cycles` theo `projectId`; nếu chưa có → tạo mới (`durationWeeks` = `stageDurationWeeks` hiện tại hoặc mặc định 2, `stageAtStart` = `selectedStage`). Lưu ý: `stageAtStart` là `varchar` tự do, không có enum/validate ở DB hay service (`twelve-week-year.service.ts` không check giá trị hợp lệ) — giá trị mặc định hiện tại `"S1_PROBLEM_VALIDATION"` dùng quy ước đặt tên khác với `P0_DISCOVERY`/`P1_PROBLEM_VALIDATION` của `projects.lifecycleStage`, nhưng vì cột không ràng buộc nên ghi `selectedStage` (`"P0_DISCOVERY"` hay `"P1_PROBLEM_VALIDATION"`) vào đây vẫn hợp lệ — chỉ là không nhất quán tên gọi giữa 2 nơi, cần nêu rõ khi ai đó đọc lại giá trị này sau này.
3. Tìm `weekly_plans` theo `cycleId` + `weekNo=1`; nếu chưa có → tạo mới với `focus`/`mission` = `firstWeekOutcome`; nếu đã có và `firstWeekOutcome` thay đổi → update `focus`/`mission`.
4. Diff `actions` (mới) với `existing.firstWeekActions` (cũ, đọc từ row hiện tại trước khi update):
   - **Action mới xuất hiện** (id chưa tồn tại trong existing) → tạo `weekly_commitments` row (title, weeklyPlanId, initiativeId=null) + tạo `tasks` row dùng **`id = action.id`** (ép kiểu BigInt), `weeklyCommitmentId` = commitment vừa tạo, `source = "project_kickoff"` + insert `task_projects` (taskId, projectId).
   - **Action biến mất** (có trong existing, không còn trong mới — do `removeAction`) → set `weekly_commitments.status = "cancelled"` + soft-delete task tương ứng (`tasks.deletedAt = now()`).
   - Action giữ nguyên id — không làm gì (không có UI sửa title nên không cần đồng bộ update title).

### 3.3 Thay đổi schema (migration, Expand-only)

`services/company/shared/db/schema/operations.ts`:
- `twelveWeekCycles.projectId` — thêm `.references(() => projects.id, { onDelete: "set null" })` (xuyên schema, cần import `projects` từ `strategy.ts`).
- `tasks.weeklyCommitmentId` — thêm `.references(() => weeklyCommitments.id, { onDelete: "set null" })`.

Cả hai đều Expand (thêm constraint trên cột đã tồn tại, không đổi kiểu, không xoá gì). Vì dữ liệu hiện tại được xác nhận sẽ reset trước khi migration này chạy, không cần backfill/khớp dữ liệu cũ trước khi thêm FK.

### 3.4 Ngoài phạm vi (Non-goals)

- **Không** build UI review tuần (chấm `executionScore`/`outcomeScore`/`reflection`) — chỉ đảm bảo dữ liệu có chỗ chứa đúng để tính năng đó làm sau này không phải migrate lại.
- **Không** sửa frontend Tasks module / 12WY module — giả định 2 module này đã query theo `workspaceId`/`projectId` chung, nên task/cycle mới tự xuất hiện. Sẽ verify bằng cách chạy thử ở bước thực thi (viết trong plan), không giả định suông.
- **Không** backfill dữ liệu `project_operating_setups` cũ đã ACTIVE trước đây — theo xác nhận của user, dữ liệu sẽ reset lại từ đầu trong lúc thay đổi.
- **Không** đổi flow "Xác nhận vòng đầu" hiện tại (validate, event `PROJECT_OPERATING_SETUP_ACTIVATED`) — chỉ chèn thêm bước materialize dùng chung với `saveDraft`.
- **Không** tạo nhiều `twelve_week_cycles`/`weekly_plans` cho tuần 2, 3... — kickoff chỉ tạo tuần 1; việc tạo tuần tiếp theo (qua weekly review cadence) là tính năng riêng, chưa thiết kế ở đây.

## 4. Rủi ro / điểm cần lưu ý

- **Tên bảng "twelve_week_cycles" gây hiểu lầm**: 1 project P0 chỉ kickoff 1-2 tuần vẫn tạo 1 row trong bảng "12 tuần" (với `durationWeeks=2`). Đây là lựa chọn có chủ đích — bảng này là container "nhịp vận hành" chung, không bắt buộc đúng 12 tuần (field `durationWeeks` vốn đã configurable). Founder xem "Kế hoạch 12WY" sẽ thấy 1 cycle 2 tuần thay vì 12 — chấp nhận được vì đúng bản chất, nhưng cần lưu ý khi làm UI 12WY sau này (hiển thị đúng `durationWeeks` thay vì hard-code "12 tuần").
- **Transaction cho `saveProjectOperatingSetup`**: hàm này hiện KHÔNG chạy trong `db.transaction()` (khác với `activateProjectOperatingSetup`). Phải bọc transaction khi thêm các insert cycle/plan/commitment/task để tránh ghi nửa chừng.
- **`weekly_commitments` không có `deletedAt`**: dùng `status = "cancelled"` làm quy ước xoá mềm (nhất quán với `tasks.status` đã có giá trị `"cancelled"`).

## 5. Câu hỏi còn mở cho user (cần trả lời trước khi viết plan)

Không có — user đã xác nhận từng phần qua hội thoại (không backfill, materialize ngay khi addAction, không OKR, không cần gộp schema). Đây là bản tổng hợp cuối để user xác nhận trước khi chuyển qua viết implementation plan.
