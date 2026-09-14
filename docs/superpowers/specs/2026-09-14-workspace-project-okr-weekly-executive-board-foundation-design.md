# Design: Hoàn thiện nền tảng Workspace/Project lifecycle, OKR, Weekly execution, Task, và Executive Board activation theo stage

**Ngày:** 2026-09-14
**Trạng thái:** Draft — chờ founder review

## Bối cảnh

Founder xác định 5 vùng là "nền tảng" cần hoàn thiện trước khi nối Skill
layer (Skill kết nối ở đợt sau, ngoài phạm vi doc này): Workspace, Project,
OKRs, Weekly (tên cũ "12WY"), Tasks — cộng với việc kích hoạt 13 role
Executive Board theo từng giai đoạn workspace/project.

Audit code thật (không dựa tài liệu cũ) cho thấy:

- **Workspace & Project lifecycle**: backend (schema, CAS transition,
  `*_lifecycle_events` audit trail, RBAC, test) đã hoàn thiện 100% theo đúng
  nguyên tắc "chuyển giai đoạn thủ công, không tự động" trong CLAUDE.md.
  Khoảng trống duy nhất là **frontend chưa có UI** để thực hiện transition
  hoặc xem lịch sử.
- **OKR**: backend (`okr.handler.ts`) đầy đủ route CRUD + publish + checkin +
  progress. Frontend (`okr_service.dart`) toàn bộ bị tắt cứng
  `ApiClient.removed(...)` từ đợt Founder Trial R1 scope-cut — không gọi API
  thật nào.
- **Weekly execution** (tên cũ "12WY"): chỉ MỘT bộ bảng DB thật
  (`twelve_week_cycles`/`weekly_plans`/`weekly_commitments`, schema
  `operating`), được nhiều lớp service cùng chạm vào. Đường sống thật mà
  frontend đang dùng đúng là `project-operating-loop.service.ts`
  (route `/operations/projects/:id/operating-loop/*`) — founder đã tự chọn
  `durationWeeks` (1-12) khi tạo cycle. `twelve_week_service.dart` (Flutter)
  là file mồ côi gọi `/execution/*` không tồn tại — không được dùng ở đâu.
  `twelve-week-year.handler.ts` (route cũ `/operations/cycles`) vẫn sống
  nhưng tự khoá tính năng resize và trỏ sang một route
  (`PATCH .../operating-cycle`) **không tồn tại** — dead-end thật.
  OKR hiện **không tự sinh** weekly plan — liên kết Objective→Cycle→Weekly
  là thao tác thủ công rời rạc.
- **Tasks**: module hoàn thiện nhất — CRUD, claim, schedule, advance đã có.
  Cột `deleted_at` đã tồn tại trên bảng `tasks` (đúng convention soft-delete
  toàn hệ thống) nhưng **chưa có bất kỳ endpoint/service nào set giá trị
  này** — soft-delete chưa được wire. Task hiện chỉ liên kết Week/KR gián
  tiếp qua `weeklyCommitmentId` → `weeklyCommitment.purposeRef`/qua
  `initiativeId` → `initiative.keyResultId`; không có cột trực tiếp.
- **13 role "Executive Advisory Board"** (project-scoped, không phải
  `workspace_operating_roles`): cả 13 role (`chief_of_staff, cfo, cmo, coo,
  cro, cpo, cco, chro, ciso, gc, cdo, caio, vpe`) đã `READY` (AgentSpec +
  skillpack + service `executive-role-activation.service.ts`). Activation
  hiện chỉ qua 2 preset tĩnh (`startup-discovery`, `startup-build-launch`)
  founder tự chọn thủ công. **Không có bất kỳ liên kết nào** với
  `lifecycle_stage` của project (0 kết quả grep) — đây là thiết kế hoàn toàn
  mới.

## Mục tiêu

Hoàn thiện luồng nền tảng end-to-end: founder tạo Workspace → tạo Project →
chuyển stage thủ công có kiểm soát → OKR sinh khung Weekly execution → Task
gắn đúng Week/KR → Executive Board gợi ý đúng role theo stage hiện tại của
Project. Dọn các phần chết/gãy phát sinh từ đợt Founder Trial R1 scope-cut
để không để lại code gây hiểu nhầm ("nhìn như tính năng nhưng không chạy").

**Ngoài phạm vi (non-goals):** kết nối Skill vào Agent/Workflow (đợt sau);
build tính năng nâng cao của Weekly cũ (stage-gate/milestones/contract
UI/compile/week13 — không có backend, không nằm trong yêu cầu lần này).

## 1. Workspace & Project lifecycle UI

Backend đã đủ (`PATCH /identity/workspaces/:id/lifecycle`,
`PATCH /operations/projects/:id/lifecycle`, `GET .../lifecycle/events`).
Chỉ cần nối dây frontend:

- Thêm section "Lifecycle" trong Workspace Settings và Project Settings:
  hiển thị stage hiện tại (badge), nút "Chuyển giai đoạn tiếp theo" (tiến 1
  bậc — không cần rationale) và "Lùi giai đoạn" (bắt buộc nhập `rationale`
  trước khi gọi API — khớp đúng rule CAS `stage_version` đã có ở backend).
  Ẩn nút nếu người dùng không phải founder/co-founder/admin (check quyền ở
  FE chỉ để UX — backend đã enforce `assertLifecyclePrivileged`, FE không
  thay thế cho check đó).
- Thêm tab "Lịch sử" gọi `GET .../lifecycle/events`, hiển thị timeline
  (from_stage → to_stage, actor, rationale, thời gian) — reuse pattern audit
  trail UI nếu đã có component tương tự trong codebase (kiểm tra lúc lên
  plan chi tiết, không đoán trước ở đây).
- Không đổi schema/service backend.

## 2. OKR — nối dây frontend

Viết lại `frontend/lib/modules/strategy/services/okr_service.dart`: thay
toàn bộ method `ApiClient.removed('r1-removed:...')` bằng gọi thật:

| Method | Endpoint thật |
|---|---|
| list/create OKR cycle | `GET/POST /operations/okr-cycles` |
| create/get/update/delete Objective | `POST /operations/objectives`, `GET/PUT/DELETE /operations/objectives/:id` |
| publish Objective | `POST /operations/objectives/:id/publish` |
| create/get/update/delete Key Result | `POST /objectives/:objectiveId/key-results`, `GET/PUT/DELETE /operations/key-results/:id` |
| checkin Key Result | `POST /operations/key-results/:id/checkin` |
| xem progress | `GET /operations/objectives/:id/progress` |

Bỏ comment "PLANNED, shell kept..." ở đầu file — module giờ live thật.
Controller/view hiện có (`modules/strategy/`) không cần sửa nếu model đã
khớp DTO backend — plan chi tiết sẽ kiểm tra lại field-by-field.

## 3. OKR → Weekly generator (thiết kế mới)

**Trigger**: khi founder publish một Objective đã có ≥1 Key Result
(`POST /objectives/:id/publish` thành công), frontend mở dialog xác nhận
"Tạo Operating Cycle cho Objective này?" với số tuần gợi ý mặc định 12
(chỉnh được 1-12, tái dùng đúng UI ChoiceChip đã có ở
`project_analysis_flow_view.dart`). Founder có thể bỏ qua — publish Objective
không bắt buộc phải tạo cycle ngay.

**Nếu founder xác nhận**: gọi tuần tự API đã sống thật của
`project-operating-loop.service.ts`:
1. `createCycle(projectId, durationWeeks)` — cycle mới, `sourceObjectiveId`
   lưu lại (cần thêm cột nullable `source_objective_id` trên
   `twelve_week_cycles` nếu chưa có — kiểm tra lúc viết plan) để biết cycle
   này sinh ra từ Objective nào.
2. Tạo khung `weekly_plans` rỗng cho từng `weekNo` 1..N (không tự tạo
   initiative/commitment — founder/agent gắn KR vào weekly plan thủ công sau
   đó như luồng hiện tại của `project-operating-loop.*`).

Generator chỉ dựng khung, không suy đoán initiative — giữ đúng nguyên tắc
"không tự quyết định business logic thay người dùng".

## 4. Dọn dẹp Weekly execution (loại bỏ phần không phù hợp)

- Xoá `frontend/lib/modules/strategy/services/twelve_week_service.dart` —
  file mồ côi, gọi `/execution/*` không tồn tại, xác nhận lại 0 call site
  trước khi xoá.
- Xoá phần route/service trùng lặp trong `twelve-week-year.handler.ts`
  (`/operations/cycles`, `/operations/twelve-week-plans`,
  `/operations/weekly-commitments`) **sau khi xác nhận lại lúc viết plan**
  không còn call site thật nào (kể cả test) ngoài chính nó — vì
  `project-operating-loop.*` đã là đường sống duy nhất. Nếu có call site
  còn dùng, giữ lại và chỉ sửa dead-end resize (mục dưới).
- Sửa dead-end: `updateCycle` trong `twelve-week-year.handler.ts` hiện chặn
  đổi `durationWeeks` và trỏ sang route không tồn tại
  (`PATCH .../operating-cycle`) — nếu route này (hoặc tương đương) chưa có ở
  `project-operating-loop.handler.ts`, cần quyết định: (a) bỏ hẳn khả năng
  resize cycle đang chạy (xoá thông báo, trả lỗi rõ ràng "not supported"),
  hoặc (b) thêm route resize thật. Plan chi tiết sẽ chọn theo mức ưu tiên —
  mặc định đề xuất (a) vì resize cycle đang chạy giữa chừng không phải yêu
  cầu của founder lần này.

## 5. Tasks — soft-delete + liên kết Week/KR trực tiếp

- **Soft-delete**: thêm `POST /operations/tasks/:id/delete` (hoặc
  `DELETE /operations/tasks/:id` — quyết theo convention REST hiện có ở
  `task.handler.ts` lúc viết plan) — set `tasks.deleted_at = now()`. Cột đã
  tồn tại và đã được filter (`isNull(tasks.deletedAt)`) ở mọi query hiện có
  trong `task.service.ts` — chỉ cần thêm hành động set giá trị, không cần
  sửa migration.
- **Liên kết trực tiếp Week + KR (nullable)**: thêm 2 cột mới trên bảng
  `tasks` (migration mới, Expand-only theo Encore Guardrail #4):
  - `weekly_plan_id` (bigint, nullable, FK → `weekly_plans.id`,
    `onDelete: set null`) — task có thể gắn thẳng vào 1 tuần cụ thể kể cả
    khi chưa qua `weeklyCommitment`.
  - `key_result_id` (bigint, nullable, FK → `key_results.id`,
    `onDelete: set null`) — task có thể gắn thẳng KR kể cả khi chưa qua
    `initiative`.
  - Cả hai đều **nullable**, không backfill giả cho task cũ. Khi tạo task từ
    weekly commitment/initiative như luồng hiện tại, tự động điền 2 cột này
    từ context (denormalize để đọc nhanh) thay vì bắt UI phải chọn lại.
  - Cập nhật `ProjectActivityDetailDTO`/`task.handler.ts` response để trả 2
    field mới cho FE hiển thị badge Week/KR ngay trên Task card.

## 6. Executive Board activation — cấp Workspace, gợi ý theo Project stage (thiết kế mới)

**Phân tách 2 khái niệm** (chốt sau thảo luận thiết kế 2026-09-14):

- **Role catalog** (13 role: định nghĩa, AgentSpec, skillpack, label) — đã là
  global/platform-level từ trước (`shared/contracts/executive-advisor-roles.json`),
  không đổi.
- **Role activation** (role này có đang thực sự "phục vụ" hay không) —
  **chuyển từ Project-scoped sang Workspace-scoped cho TOÀN BỘ 13 role**,
  không chỉ 4 role duy trì. Lý do: một CFO/CRO/COO... là chức danh cấp công
  ty — dù workspace có nhiều Project chạy song song ở stage khác nhau, công
  ty chỉ có 1 CRO thật, không tách theo từng project. Xác nhận qua code:
  `project_executive_deliberations*` (buổi họp tư vấn) chỉ tham chiếu
  `roleKey` dạng chuỗi/jsonb (`selectedRoles`, `roleKey` trên bảng analyses),
  KHÔNG có FK tới activation record — chuyển activation lên Workspace không
  phá vỡ deliberation nào (deliberation vẫn project-scoped như cũ, đúng bản
  chất "buổi họp bàn về project X").

**Bảng mapping cố định** (founder đã chốt) — dùng để TÍNH GỢI Ý theo stage
của TỪNG Project riêng biệt (độc lập với nơi lưu activation), đặt trong file
cấu hình mới `services/company/operations/services/executive-board-stage-presets.ts`:

| Project stage | Role được gợi ý nổi bật cho Project này |
|---|---|
| P0–P1 (Discovery) | chief_of_staff, cfo, cmo, cpo |
| P2–P3 (Solution & Build) | coo, vpe, ciso, gc, cdo, caio |
| P4 (Go-to-market) | cro, cco |
| P5–P6 (Operate & Scale) | chro |

Role **duy trì xuyên suốt** (`chief_of_staff, cfo, cmo, cpo`): không bao giờ
nằm trong danh sách "gợi ý deactivate" ở bất kỳ stage nào — chỉ mất active
nếu founder tự suspend thủ công. Về mặt kỹ thuật, chúng chỉ là 4 trong 13
role của cùng 1 bảng activation Workspace — không có cơ chế lưu trữ đặc biệt
nào khác biệt 9 role còn lại, khác biệt DUY NHẤT nằm ở quy tắc gợi ý này.

**Schema mới** (Expand-only, không xoá bảng cũ trong đợt này):
`operating.workspace_executive_role_activations`
(`id, workspace_id, role_key, state, version, actor_id, created_at, updated_at`,
unique trên `(workspace_id, role_key)`) +
`operating.workspace_executive_role_activation_events` (audit trail
append-only, cùng pattern với bản project-scoped cũ). Bảng cũ
`project_executive_board_settings`/`project_executive_role_activations`/`..._events`
và 2 preset tĩnh (`startup-discovery`, `startup-build-launch`) bị **ngừng sử
dụng trong code** (không DROP bảng — migration destructive cần release riêng
theo CLAUDE.md Encore Guardrail #4).

**Cơ chế** (không tự động — đúng nguyên tắc CLAUDE.md):
1. `getProjectExecutiveRoleStates(ctx, projectId)` (read-model hiện có, dùng
   bởi UI mọi Project) đổi nguồn dữ liệu activation sang đọc
   `workspace_executive_role_activations` theo `workspace_id` (không lọc
   `project_id`) cho cả 13 role — mọi Project trong cùng workspace nhìn thấy
   CÙNG MỘT trạng thái ACTIVE/DISABLED.
2. Sau khi `PATCH /operations/projects/:id/lifecycle` transition thành công,
   endpoint `GET /operations/projects/:id/executive-board/stage-suggestion`
   trả về `{ stage, toActivate: Role[], toSuggestDeactivate: Role[] }` — tính
   diff giữa preset của stage MỚI CỦA PROJECT NÀY và trạng thái activation
   Workspace hiện tại, loại trừ nhóm role duy trì khỏi `toSuggestDeactivate`.
3. Founder bấm "Kích hoạt" 1 role từ dialog gợi ý → gọi
   `POST /operations/workspaces/:workspaceId/executive-roles/:roleKey/activate`
   (endpoint mới, Workspace-scoped) — ảnh hưởng ngay tới mọi Project khác
   trong cùng workspace. Endpoint Project-scoped cũ
   (`POST /operations/projects/:id/executive-roles/:roleKey/activate`) không
   còn nằm trong luồng chính — mức xử lý cụ thể (giữ trả lỗi rõ ràng hướng
   dẫn dùng endpoint mới, hay bỏ hẳn) quyết định lúc viết plan chi tiết theo
   mức rủi ro breaking change với call site hiện có.
4. Không cần sửa preset `startup-discovery` nữa — khái niệm "chọn preset
   theo từng project" không còn áp dụng khi activation là 1 trạng thái
   Workspace duy nhất cho cả 13 role.

## 7. Dọn dẹp khác (không liên quan trực tiếp nhưng phát hiện trong audit)

- Xoá `frontend/lib/modules/settings/workforce/views/profile_composition_view.dart`
  (orphan — không controller, không reference ở bất kỳ đâu khác). Xác nhận
  lại bằng grep ngay trước khi xoá ở bước thực thi.
- Xoá `frontend/lib/modules/organization/services/business_pack_service.dart`
  (10 endpoint `/business/packs/*`, 0 route backend tương ứng — dead code).

## Kiểm thử / Verify

- Backend: test mới cho OKR→Weekly generator (publish Objective → tạo cycle
  → weekly_plans đúng số tuần), test cho `executive-board/stage-suggestion`
  (đúng diff theo bảng mapping, role duy trì không bị gợi ý deactivate), test
  soft-delete Task (deleted_at set, không còn xuất hiện ở list/get).
  Chạy `make services-test-company`.
- Migration mới (2 cột trên `tasks`, cột `source_objective_id` trên cycle
  nếu cần): `node scripts/migrate.mjs` / `make services-migrate-company`,
  đúng nguyên tắc Expand-only.
- Frontend: test cho OKR service (mock response thật thay vì assert
  `unavailable`), test dialog OKR→Weekly generator, test dialog Executive
  Board suggestion, test Task card hiển thị Week/KR badge và hành động xoá
  (soft-delete). `make frontend-test`.
- `make company-boundary-check`, `make encore-handler-boundary-check`,
  `make frontend-api-contract-check` (route mới phải có trong
  `shared/contracts/mvp-surface.json`).
- Cuối cùng `make verify` trước khi báo hoàn tất (CLAUDE.md quy tắc #11).
