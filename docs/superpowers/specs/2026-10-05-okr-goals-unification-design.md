# Dự án A0 — Hợp nhất Goals / OKR về một mô hình chuẩn

Ngày: 2026-10-05 · Trạng thái: DRAFT chờ duyệt · Chạy **trước** Dự án A (ancestry) và B (verifier)

Quyết định đã chốt với chủ dự án (2026-10-05): dữ liệu hiện có chỉ là dữ liệu thử, được phép reset; hỗ trợ objective cấp công ty và cấp project, căn chỉnh qua `parent_objective_id`.

## 1. Vấn đề (đã kiểm tra trong code)

| # | Vấn đề | Bằng chứng |
|---|---|---|
| 1 | Hai họ bảng trùng nghĩa: `strategy.objectives`+`cosa_key_results` và `strategy.okr_objectives`+`key_results` | `028_startup_os_core_schema.up.sql`, `shared/db/schema/{goals,operations}.ts` |
| 2 | `okr_objectives` không trỏ về goals; goals chỉ nối xuống qua `projects.objective_id` | schema `operations.ts:367`, FK `fk_projects_objective` |
| 3 | Tiến độ chia đôi: task/agent ghi `key_results`, goal tính từ `cosa_key_results` | `goals.service.ts:153,336` |
| 4 | `cosa_key_results` thiếu `workspace_id` và unique `(id, workspace_id)` | DDL migration 028 |
| 5 | `okr_cycles` tồn tại nhưng `okr_objectives` không có `cycle_id`; `createObjectiveService` kiểm tra `cycleId` rồi bỏ | `okr.service.ts:176-226` |
| 6 | `createObjectiveService` tự chọn project đầu tiên khi thiếu `projectId` | `okr.service.ts:~200` |
| 7 | Hai bộ API: `/operations/objectives*` và `/operations/cosa/objectives*` | `okr.handler.ts`, `goals.handler.ts:192-217` |
| 8 | Hai KR lệch kiểu (`NUMERIC` vs `double precision`) và lệch trạng thái | schema hai bảng |
| 9 | `progress_pct`, `weight` nhập tay ở `strategy.objectives` | migration 028 |
| 10 | Ba khái niệm thời gian rời nhau: `goals`, `okr_cycles`, `twelve_week_cycles` | schema |

## 2. Mô hình đích

```
goals                       tầm nhìn / chiến lược / chiến thuật / sprint, cây theo parent_id (GIỮ)
okr_cycles                  kỳ OKR (quý…)            (GIỮ, nay được gắn thật)
  okr_objectives            MỘT bảng objective
    goal_id        → goals              NOT NULL
    cycle_id       → okr_cycles         NULL được (draft), bắt buộc khi publish
    scope          'company' | 'project'
    project_id     → projects           NULL khi scope=company; NOT NULL khi scope=project
    parent_objective_id → okr_objectives  (chỉ trỏ tới scope=company, cùng goal, cùng workspace)
    └─ key_results           MỘT bảng KR (giữ cấu trúc hiện có: metric, evidence, scoring)
         └─ initiatives → tasks   (GIỮ)
projects.objective_id → okr_objectives(id)     (dự án phục vụ objective nào)
twelve_week_cycles.source_objective_id → okr_objectives   (GIỮ)
```

Chuỗi ancestry cho Dự án A (project là khung chứa, `tasks.project_id` và `initiatives.project_id` đều NOT NULL):

```
goal (leo parent_id)
 └─ objective công ty         scope=company
     └─ project               projects.objective_id → objective công ty
         └─ objective dự án   scope=project, project_id = project này
              └─ key_result
                   └─ initiative   (project_id)
                        └─ task    (project_id)
```

Đọc ngược từ task: `task → initiative → KR → objective dự án → project → objective công ty → goal`. Project phải xuất hiện tường minh; một task luôn thuộc đúng một project, và `task.project_id` phải trùng `project_id` của objective dự án qua KR/initiative (thêm kiểm tra nhất quán).

**Quyết định (2026-10-05):** giữ cả hai đường `projects.objective_id` và `okr_objectives.parent_objective_id`, kèm ràng buộc đồng nhất: với objective `scope=project`, `parent_objective_id` phải bằng `projects.objective_id` của project đó (hoặc NULL, khi đó coi như thừa kế từ project). Postgres CHECK không tham chiếu được bảng khác nên dùng trigger `BEFORE INSERT/UPDATE` trên `okr_objectives` và trên `projects` (khi đổi `objective_id`, chặn nếu còn objective dự án trỏ `parent_objective_id` khác). Lưu ý đây là ràng buộc dư; nếu về sau không cần căn chỉnh riêng từng objective thì bỏ `parent_objective_id`.

Quy tắc:
- Tiến độ objective **tính ra** từ KR (view `strategy.v_objective_progress`), không lưu `progress_pct` nhập tay. Tiến độ goal tính từ objective con.
- Mọi bảng có `workspace_id NOT NULL` và `UNIQUE (id, workspace_id)`; FK ghép khi tham chiếu (theo mẫu `uix_okr_objectives_id_workspace`).
- Không còn tự chọn project: `scope='project'` bắt buộc `projectId`.
- Objective công ty không có task trực tiếp; chỉ cung cấp tiêu chí và tiến độ gộp từ objective project con.

### 2.1 Điều chỉnh sau khi đọc code (2026-10-05)

Các điều chỉnh này thay thế các câu tương ứng ở các mục khác của spec:

- `goal_id` **chỉ bắt buộc cho objective `scope=company`**; objective `scope=project` để NULL, goal của nó suy ra qua `parent_objective_id` (hoặc `projects.objective_id`). Lý do: project có thể `intentionally_unlinked`/`pending_review` (R&D, discovery) và vẫn cần OKR; ép `goal_id` sẽ chặn chúng và làm vỡ mọi test seed SQL thô.
- `scope` có DEFAULT `'project'` để mã và test hiện có (`INSERT ... project_id ...`) giữ nguyên hành vi.
- **Không bắt buộc `cycle_id` khi publish** (bỏ yêu cầu cũ); chỉ lưu `cycle_id` nếu truyền. YAGNI và tránh vỡ luồng publish hiện có.
- **Không tạo view `v_objective_progress`**: tiến độ tính trong TypeScript bằng `computeKeyResultProgress`/`computeObjectiveScore` (`okr-scoring.service.ts`), đã đúng cho KR giảm/milestone/range. SQL view chỉ cần cho `v_goal_tree`/`fn_goals_needing_review` (viết lại theo họ OKR, đếm không dùng `current >= target`).
- Bỏ việc chọn project ngẫu nhiên: thiếu `projectId` chỉ được chấp nhận khi workspace có **đúng một** project (giữ tương thích test hiện có); nhiều project thì lỗi `invalidArgument`.
- **Xóa hẳn** `/operations/cosa/objectives*` và `/operations/cosa/key-results*` thay vì hợp nhất: không có trong `mvp-surface.json`, không có trong frontend; chỉ `tests/quality/test_route_auth_allowlist.py` có thể tham chiếu.
- Migration chia theo expand → contract: `038` (cộng thêm cột, ràng buộc, trigger cơ bản) rồi `039` (đổi FK `projects.objective_id`, trigger liên bảng, xóa họ 1, viết lại view/function). Dự án A (done_criteria) dời sang `040`.

## 3. Phạm vi thay đổi

### 3.1 Database (Company)
Migration `038_okr_goals_unification.up.sql` + `.down.sql` (thứ tự Agent → COSA → Company):
1. Reset dữ liệu thử: `TRUNCATE` họ 1 (kèm cảnh báo trong header migration); không backfill.
2. `ALTER strategy.okr_objectives`: thêm `goal_id`, `cycle_id`, `scope` (CHECK), `parent_objective_id`; `project_id` thành nullable với CHECK ràng buộc theo `scope`; index theo `(workspace_id, goal_id)`, `(workspace_id, cycle_id)`, `parent_objective_id`.
3. Ràng buộc căn chỉnh (CHECK cho phần cùng bảng, trigger cho phần liên bảng):
   - CHECK: `scope='company'` ⇒ `project_id IS NULL` và `parent_objective_id IS NULL`; `scope='project'` ⇒ `project_id IS NOT NULL`.
   - Trigger trên `okr_objectives`: `parent_objective_id` phải trỏ objective `scope='company'`, cùng `goal_id` và `workspace_id`; với `scope='project'` phải bằng `projects.objective_id` của `project_id` (hoặc NULL).
   - Trigger trên `projects`: đổi `objective_id` bị chặn nếu còn objective dự án có `parent_objective_id` khác giá trị mới; `objective_id` phải trỏ objective `scope='company'`.
   - Kiểm tra nhất quán chuỗi: `initiative.project_id`, `task.project_id` phải trùng `project_id` của objective dự án qua KR (kiểm ở service và test; DB chỉ ép nếu chi phí chấp nhận được).
4. Đổi FK `projects.objective_id` từ `strategy.objectives` sang `strategy.okr_objectives`.
5. `DROP strategy.cosa_key_results`, `strategy.objectives`; viết lại `v_goal_tree`, `fn_goals_needing_review` theo họ OKR; thêm `v_objective_progress`.
6. Cập nhật `scripts/preflight-workspace-tenancy.sql` và chạy `make schema-fingerprint-write`.

### 3.2 Company service (TypeScript)
- `shared/db/schema/goals.ts`: bỏ `objectives`, `cosaKeyResults`; `operations.ts`: sửa `okrObjectives` (sửa tay, Drizzle không sinh).
- `okr.service.ts`: `createObjectiveService` nhận `goalId`, `scope`, `cycleId`, `parentObjectiveId`; lưu `cycle_id`; bỏ fallback project đầu tiên; thêm validate căn chỉnh. Publish yêu cầu `cycle_id`.
- `goals.service.ts`: `getGoalTreeService`, `getGoalsNeedingReviewService`, `completeGoalService` đọc/ghi qua `okr_objectives`/`key_results`; bỏ `createObjectiveService`/`addKeyResultService`/`updateKeyResultValueService` bản Startup OS (gộp vào `okr.service.ts`).
- `discovery-project.service.ts`: `link` và `roll_to_new_goal` dùng `okr_objectives` (`roll_to_new_goal` tạo objective `scope='project'` thuộc goal mới).
- `marketing-mvp.service.ts` và handler: kiểm tra phụ thuộc vào `strategy.objectives`; chuyển sang họ OKR nếu có.
- API: hợp nhất `/operations/cosa/objectives*` và `/operations/cosa/key-results*` vào `/operations/objectives*`/`/operations/key-results*`; giữ `/operations/goals*`. Cập nhật `mvp-surface.json`, chạy `make mvp-contracts-gen`, `route-inventory-check`, `frontend-api-contract-check`, `route-auth-allowlist-check` (có `tests/quality/test_route_auth_allowlist.py`).

### 3.3 Agent / COSA
- `apps/cosa/capabilities/okr_write.py`: thêm `goal_id`, `scope`, `parent_objective_id` vào tạo objective; giữ quy ước "tham chiếu bằng title, không dùng id".
- `startup_os_goals.py`: `goal.tree_read` và `goal.advisory` đọc từ họ OKR.
- Không đổi `instructions`/`capability_refs` của AgentSpec ⇒ không đổi hash; nếu bắt buộc đổi thì nâng pin ở `ai-member.service.ts`.

### 3.4 Frontend (Flutter)
- Kiểm tra màn dùng `/operations/cosa/*`; chuyển sang endpoint hợp nhất. File liên quan: `strategy/views/strategy_view.dart`, `strategy/models/mvp_strategy_models.dart`, `projects/views/widgets/okr_section.dart`, `projects/models/project_operating_loop.dart`.
- Chạy `make frontend-test frontend-analyze`.

### 3.5 Test cần cập nhật
`services/company/operations/tests/` (`okr.test.ts`, `startup-os.test.ts`, `startup-os-auth.test.ts`, `composite-uniqueness.test.ts`, `execution-outcome.test.ts`, `executive-context.test.ts`, `project-operating-loop*.test.ts`, `task-outcome-*.test.ts`, `mvp-okr-twelve-week.test.ts`, `_helpers.ts`), `commercial/tests/mvp-marketing.test.ts`, `shared/tests/golden-path.e2e.test.ts`, `tests/apps/cosa/test_okr_capabilities.py`, `tests/db_baseline_candidate/test_startup_core_schema.py`, `tests/e2e/test_startup_core_clean_baseline.py`, `tests/e2e/test_ai_initiative_operating_system.py`. Test mới: căn chỉnh company↔project, ràng buộc `scope`, tiến độ gộp, tenancy của KR.

## 4. Thứ tự thực hiện

1. Migration + schema Drizzle + view (đứng được riêng, test DB).
2. `okr.service.ts` (thêm trường, validate, bỏ fallback).
3. `goals.service.ts` + `discovery-project.service.ts` + marketing.
4. Hợp nhất API, sinh contract, sửa allowlist.
5. Capability agent.
6. Frontend.
7. Xóa code họ 1 còn sót; chạy toàn bộ gate.

Mỗi bước phải xanh trước khi sang bước sau.

## 5. Rủi ro

- Phạm vi rộng (~35 file chạm OKR, cộng frontend và agent). Cần chạy từng bước, không gộp.
- Đổi API công khai làm vỡ client; chưa có dữ liệu thật nên chấp nhận, nhưng frontend và agent phải đổi cùng lúc.
- `TRUNCATE` không đảo ngược: chỉ chạy sau khi chủ dự án xác nhận lại môi trường (dev/staging) lúc thực thi.
- Drizzle sửa tay có thể lệch với DDL; dùng `schema-fingerprint-check` và test baseline để bắt.
- Dự án A và B cần đổi số migration: A0 lấy `038`, A (done_criteria) dời sang `039`.

## 6. Xác minh

```bash
make migration-check schema-fingerprint-check tenancy-check
make services-test-company
make apps-cosa-test
make mvp-contracts-check route-inventory-check frontend-api-contract-check route-auth-allowlist-check
make frontend-test frontend-analyze
make verify
```

Kiểm tra thủ công: tạo goal → objective công ty (cycle Q4) → objective project trỏ `parent_objective_id` → KR → initiative → task; check-in KR và xác nhận tiến độ objective và goal tăng; thử tạo objective project không có `projectId` phải bị từ chối.

## 7. Điểm còn cần xác nhận lúc thực thi

- Môi trường nào được phép `TRUNCATE` (dev, staging) và production có dữ liệu thật không.
- Frontend có đang gọi `/operations/cosa/*` không (cần grep xác nhận trước bước 6).
