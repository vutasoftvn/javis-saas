# Implementation Plan: Startup OS Data Architecture & Operations (COSA v1.0)

**Date:** 2026-09-18  
**Reference Specification:** [`docs/cosa.md`](file:///Volumes/SSD/javis-saas/docs/cosa.md)  
**Status:** Approved for Direct Dev Implementation (Lưu Plan)  

---

## 1. Quyết định Kiến trúc & Phản hồi từ Founder

Dựa trên phản hồi và phê duyệt từ Founder:
1. **Môi trường:** Đang ở giai đoạn phát triển (dev stage) nên **sửa đổi trực tiếp (direct refactor)**, không cần cơ chế chạy song song (dual-write) phức tạp hay giữ bảng cũ không cần thiết.
2. **Onboarding Mechanism:** **Option B** — Triển khai đồng thời cả **REST/Encore API Form-based Wizard** trên UI và **Conversational Chat Agent** (`/cs:setup`, `/cs:update`) qua Agent Platform.
3. **ID Strategy:** Thống nhất sử dụng **Snowflake ID (BIGINT, 64-bit)** sinh tại application layer thông qua generator có sẵn tại `services/company/shared/services/snowflake.service.ts`.
4. **Hợp nhất Domain Mục tiêu:** Thực hiện chuyển đổi dứt điểm từ **`okr_cycles` → `goals`** (nested tree), xóa bỏ sự phân mảnh giữa cycle và goal.

---

## 2. Mục tiêu & Nguyên lý Cốt lõi

Triển khai trọn vẹn kiến trúc dữ liệu và các luồng vận hành của **Startup OS (COSA v1.0)** theo [docs/cosa.md](file:///Volumes/SSD/javis-saas/docs/cosa.md):
1. **Tenant Đồng nhất (`Workspace = Company = Tenant`):** Đơn vị tenant duy nhất.
2. **Cây Goal Đa tầng (`goals` nested tree):** Phân cấp Vision (3-5 năm) → Strategic (12 tháng) → Tactical (4-12 tuần) → Sprint (1-4 tuần) trong cùng một bảng tự tham chiếu `parent_id`.
3. **Onboarding 7 chiều (BSC Multi-Cadence):**
   - **Fast (14 ngày):** `stage_scale`, `challenges`.
   - **Medium (60–90 ngày):** `team_culture` (60d), `market` (60d), `goals_ambition` (90d).
   - **Slow (180 ngày):** `identity`, `founder`.
4. **Append-Only (`is_current`) & Immutable Snapshot:**
   - Cập nhật chiều: `INSERT` bản ghi mới với `is_current = true`, trigger demote bản ghi cũ.
   - Mỗi lần cập nhật tạo `onboard_snapshots` (JSONB `full_context`). Goal gắn liền với snapshot lúc tạo.
5. **Onboard Inform, Not Control & Double-Loop Learning:**
   - Thay đổi chiến lược chỉ cảnh báo các Goal dựa trên giả định cũ (`fn_goals_needing_review`), không tự sửa Goal.
   - Dự án thử nghiệm (`origin = discovery`, `link_status = pending_review`) được tổng hợp cuối chu kỳ để review và nâng cấp thành Objective chiến lược mới.

---

## 3. Bản đồ Phân rã Công việc (Task Breakdown)

### Phase 1: Database Migration & Schema Definition (`services/company`)

- [ ] **Task 1.1: Tạo Drizzle Schema cho Onboarding 7 chiều & Snapshots**
  - File: `services/company/shared/db/schema/onboard.ts`
  - Các bảng:
    - `onboard_sessions` (id, workspace_id, session_type, status, started_at, completed_at, duration_minutes, dimensions_touched, summary, transcript, metadata)
    - `conversation_turns` (id BIGSERIAL, session_id, turn_number, role, content, dimension, created_at)
    - `onboard_snapshots` (id, workspace_id, session_id, full_context, changed_dimensions, change_reason, is_current, captured_at)
    - `onboard_review_cadence` (id, workspace_id, dimension, cadence, interval_days, last_reviewed_at, next_due_at)
    - 7 bảng chiều: `onboard_identity` & `onboard_values`, `onboard_stage_scale`, `onboard_founders`, `onboard_team_culture`, `onboard_market` & `onboard_competitors`, `onboard_challenges`, `onboard_goals_ambition`.
    - Partial Unique Indexes cho `is_current = true` theo `workspace_id`.

- [ ] **Task 1.2: Chuyển đổi `okr_cycles` → `goals` (Nested Tree) & Cập nhật `objectives`, `key_results`, `projects`**
  - File: `services/company/shared/db/schema/goals.ts` (mới) và cập nhật `operations.ts`
  - Bảng `goals`: `id` (BIGINT), `workspace_id`, `parent_id` (self-ref), `title`, `description`, `goal_type` (`vision`, `strategic`, `tactical`, `sprint`), `start_date`, `end_date`, `duration_weeks`, `status` (`draft`, `active`, `completed`, `abandoned`), `onboard_snapshot_id`, `created_at`, `completed_at`.
  - Cập nhật bảng `objectives`: gắn trực tiếp với `goal_id`, `workspace_id`, `owner_user_id`, `weight`, `progress_pct`, `status`.
  - Cập nhật bảng `key_results`: gắn trực tiếp với `objective_id`, `metric_name`, `baseline`, `target`, `current_value`, `status`.
  - Cập nhật bảng `projects`: thêm `objective_id` (nullable references `objectives.id` ON DELETE SET NULL), `origin` (`okr_driven`, `discovery`, `maintenance`, `reactive`), `link_status` (`linked`, `pending_review`, `intentionally_unlinked`).
  - Deprecate/bãi bỏ `okr_cycles` và map các cycle cũ thành các bản ghi `goals` tương ứng.

- [ ] **Task 1.3: Viết Migration Script PostgreSQL (DDL, Triggers, Views, Functions)**
  - File: `services/company/operations/migrations/028_startup_os_core_schema.up.sql`
  - DDL tạo các bảng mới.
  - Triggers:
    - `fn_demote_current()` cho 7 bảng chiều và snapshot.
    - `fn_link_goal_to_snapshot()` auto-gán snapshot hiện tại khi tạo goal mới.
    - `fn_touch_updated_at()`.
  - Views:
    - `v_current_company_context`: Tổng hợp JSONB 7 chiều hiện tại.
    - `v_goal_tree`: WITH RECURSIVE duyệt cây phân cấp goal kèm số lượng objective và KR đạt được.
  - Functions:
    - `fn_goals_needing_review(p_workspace_id)`: Phát hiện goal active có snapshot quá hạn (tactical/sprint >14d, strategic >60d).
    - `fn_suggest_dimension_review(p_workspace_id)`: Gợi ý các chiều đến hạn/quá hạn theo nhịp BSC.

---

### Phase 2: Backend Business Plane Services & Endpoints (`services/company`)

- [ ] **Task 2.1: Onboarding Domain Service (`services/company/operations/services/onboard.service.ts`)**
  - Khởi tạo session (`initial`, `partial_update`, `event_driven`).
  - Ghi nhận `conversation_turns`.
  - Lưu trữ bản ghi chiều (`updateDimension`) theo cơ chế append-only.
  - Tạo snapshot mới (`createSnapshot`) đóng băng ngữ cảnh 7 chiều.
  - Kiểm tra và tính toán nhịp điệu review (`checkReviewCadence`, `seedReviewCadence`).

- [ ] **Task 2.2: Goals & Execution Service (`services/company/operations/services/goals.service.ts`)**
  - Tạo Goal (`createGoal`): Kiểm tra các chiều Fast (`stage_scale`, `challenges`), gợi ý cập nhật nếu stale, tự động liên kết snapshot.
  - Lấy cây phân cấp Goal (`getGoalTree`) từ `v_goal_tree`.
  - Quản lý trạng thái: Chuyển đổi trạng thái Goal, cascade sang Objectives & KRs.
  - Kiểm tra Goal cần review (`getGoalsNeedingReview`).
  - Hoàn thành Goal (`completeGoal`): Kiểm tra điều kiện hoàn thành của objectives con, cascade status, trigger review `goals_ambition`.

- [ ] **Task 2.3: Discovery Projects & Double-Loop Triage (`services/company/operations/services/discovery-project.service.ts`)**
  - Lọc các projects có `link_status = 'pending_review'`.
  - Quy trình triage cuối chu kỳ: `link` vào objective hiện có, đánh dấu `intentionally_unlinked` (R&D), `archive`, hoặc nâng cấp thành `objective` trong Goal mới.

- [ ] **Task 2.4: Form-Based REST / Encore Handlers (Option B)**
  - File: `services/company/operations/handlers/onboard.handler.ts`:
    - `POST /operations/onboard/sessions`: Khởi tạo phiên
    - `POST /operations/onboard/dimensions/:dimension`: Cập nhật trực tiếp form 7 chiều
    - `GET /operations/onboard/context/current`: Lấy snapshot và dữ liệu 7 chiều hiện tại
    - `GET /operations/onboard/cadence/status`: Kiểm tra độ tươi và cảnh báo
    - `POST /operations/onboard/snapshots`: Tạo snapshot thủ công hoặc chốt session
  - File: `services/company/operations/handlers/goals.handler.ts`:
    - `POST /operations/goals`: Tạo goal mới kèm kiểm tra cadence
    - `GET /operations/goals/tree`: Lấy danh sách cây goal
    - `GET /operations/goals/needing-review`: Lấy danh sách goal cần rà soát lại giả định
    - `POST /operations/goals/:id/complete`: Hoàn thành goal
    - `POST /operations/objectives`: Tạo objective trong goal
    - `POST /operations/objectives/:id/key-results`: Tạo KR
    - `POST /operations/projects/triage`: Xử lý discovery projects

---

### Phase 3: Agent Platform Integration (`apps/cosa` + `packages/agent`)

- [ ] **Task 3.1: Conversational Onboarding Workflow (`/cs:setup` & `/cs:update`)**
  - File: `apps/cosa/workflows/onboarding_workflow.py`
  - Triển khai kịch bản đối thoại phỏng vấn 7 chiều tự nhiên, chia thành các chặng (milestones).
  - Trích xuất dữ liệu có cấu trúc từ hội thoại của founder và gọi sang `onboard.handler` của `services/company`.
  - Hỗ trợ cập nhật nhanh các chiều Fast (~2-3 phút) khi kích hoạt `/cs:update`.

- [ ] **Task 3.2: Goal Advisory & Context Freshness Capability**
  - File: `apps/cosa/capabilities/goal_advisory_capability.py`
  - Agent tư vấn khi founder đặt mục tiêu:
    - Phân tích bối cảnh công ty hiện tại (`v_current_company_context`).
    - Đề xuất loại Goal (Tactical cho `pre_pmf`, Strategic cho `scaling`).
    - Đối chiếu mục tiêu với giá trị cốt lõi (`fire_worthy` values) và các thách thức hàng đầu (`challenges`).

---

### Phase 4: UI / Experience Plane (`frontend`)

- [ ] **Task 4.1: Màn hình Cây Mục tiêu (Goal Tree)**
  - Hiển thị cấu trúc cây mục tiêu lồng nhau đệ quy (Vision → Strategic → Tactical → Sprint).
  - Thanh tiến độ tổng hợp (rollup progress) và liên kết snapshot ngữ cảnh.

- [ ] **Task 4.2: Dashboard Độ tươi Ngữ cảnh & Cảnh báo (Context Freshness)**
  - Trực quan hóa 7 chiều theo chuẩn BSC (xanh: tươi mới, vàng: đến hạn, đỏ: quá hạn >14 ngày).
  - Modal cập nhật nhanh (Fast update modal) trước khi tạo Goal.
  - Phù hiệu cảnh báo số lượng Goal cần review giả định.

- [ ] **Task 4.3: Wizard Thiết lập Onboard 7 chiều (Form UI song song với Chat)**
  - Giao diện form nhập liệu trực tiếp 7 chiều (Option B) cho founder thích điền form thay vì trò chuyện chat.

- [ ] **Task 4.4: Modal Triage Discovery Projects cuối chu kỳ**
  - Bảng rà soát các project `pending_review` để founder phân loại và đưa vào chu kỳ tiếp theo.

---

## 5. Verification & Testing Plan

1. **Automated Schema & Trigger Tests:**
   - Kiểm tra `is_current` demote trigger hoạt động chính xác khi chèn liên tiếp 2 bản ghi cùng chiều.
   - Kiểm tra `goals` tự động liên kết với `onboard_snapshots` active gần nhất.
   - Kiểm tra view đệ quy `v_goal_tree` xuất đúng thứ bậc phân tầng.
2. **State Machine Integrity Tests:**
   - Chặn không cho `completed` goal nếu có objective con đang `active`.
   - Cascade tự động chuyển status objective sang `completed` khi goal hoàn thành.
   - Xác minh `fn_goals_needing_review` phản ứng đúng khi tạo snapshot mới.
3. **API & End-to-End Tests:**
   - Test toàn bộ các endpoint của `onboard.handler` và `goals.handler`.
   - Test luồng triage discovery project sang objective mới.
