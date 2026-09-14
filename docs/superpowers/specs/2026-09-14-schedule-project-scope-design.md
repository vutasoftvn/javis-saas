# Schedule Project Scope — Design

Status: DRAFT (chờ user review)
Ngày: 2026-09-14
Phạm vi: sub-project #1/6 trong đợt audit "Ba blocker lớn nhất" (2026-09-14) — P0.
Các sub-project còn lại (#2 Python quality gates, #3 Semantic Knowledge,
#4 Hub Workforce API, #5 Flutter data fabrication, #6 Test reliability) có
spec riêng, không nằm trong tài liệu này.

## Vấn đề

Scheduled operations run thiếu `project_id` gọi Company và lấy Project đầu
tiên của workspace (`id` giảm dần) làm ngữ cảnh chạy. Control Plane
(`services/cosa`) không lưu `project_id` trong schedule definition/execution;
worker chỉ nhận `schedule_execution_id` và tự resolve project khi thiếu. Điều
này trái với nguyên tắc "Project phải là ngữ cảnh tường minh" (CLAUDE.md quy
tắc 14), có nguy cơ chạy hoặc ghi timeline/activity vào sai Project.

Xác nhận trong code (2026-09-14):

- `services/cosa/storage/control-plane-schema.ts:210-253` —
  `workspaceScheduleDefinitions` và `workspaceScheduleExecutions` không có
  cột `project_id`/`projectId`.
- `apps/cosa/worker/handlers.py:63-87` (`_resolve_workspace_project_id`) —
  fallback gọi `GET /operations/projects` và lấy `projects[0]`.
- `apps/cosa/worker/handlers.py:1152-1169` — chỉ nhánh `agent_profile ==
  "operations"` mới trigger fallback này khi `payload.get("project_id")`
  rỗng (luôn rỗng, vì snapshot không mang field này).
- `apps/cosa/worker/handlers.py:228-277` (guard `PROJECT_TEAM_OPERATING_
  PROFILES`, = 15/16 `StartupTeamProfileKey` trừ `founder_assistant`) đã
  fail-closed đúng cho các agent_profile khác — nhưng vì schedule creation
  API hiện không có field `project_id` cho bất kỳ profile nào, mọi schedule
  không phải "operations" sẽ luôn fail với `project_context_required` (an
  toàn nhưng không dùng được).
- Flutter **chưa gọi** API tạo schedule: `frontend/lib/modules/agents/
  services/workforce_service.dart:96-111` (`listSchedules`/`createSchedule`/
  `runScheduleNow`) đều là stub trả `MvpRequestClient.unavailable(...)` với
  message "removed from the Founder Trial R1 contract". Đường tạo schedule
  duy nhất đang hoạt động thật: `apps/cosa/api/schedule_routes.py:38-78`
  (`POST /agent/schedules`) proxy sang `services/cosa` `POST /cosa/schedules`
  (`services/cosa/handlers/workspace-schedule.handler.ts:6-64`).
- Cơ chế fail-closed khi Project bị xóa/archive **đã tồn tại**:
  `apps/cosa/company/project_team_client.py:69-101`
  (`ProjectTeamClient.get_run_authority`) raise `ProjectTeamAuthorityError`
  trên bất kỳ status ≠ 200 nào từ Company — không cần viết logic mới, chỉ
  cần `project_id` đầu vào đúng.
- Pattern validate project-thuộc-workspace đã có sẵn ở Python:
  `apps/cosa/api/project_context.py:62-118` (`verify_project_context`), đang
  dùng trong `apps/cosa/api/conversation_routes.py`. `services/cosa` (TS)
  hiện **không có** client gọi `services/company` để verify project — xây
  mới hướng cross-plane call này là không cần thiết vì apps/cosa đã là điểm
  validate duy nhất trên đường tạo schedule thật.

## Kiến trúc

Tái dùng `verify_project_context()` sẵn có ở `apps/cosa` (không xây client
`services/cosa → services/company` mới, tránh thêm một hướng cross-plane
secret — đúng nguyên tắc "không nhân bản kiến trúc", CLAUDE.md quy tắc 4).

Luồng `project_id`:

```
apps/cosa/schedule_routes.py
  (validate qua verify_project_context — fail 404 sớm nếu project không
   thuộc workspace/không active)
  → services/cosa POST /cosa/schedules
    (lưu project_id vào workspace_schedule_definitions, reject nếu thiếu)
  → dispatcher (workspace-schedule.service.ts) tạo execution
    (copy project_id vào project_id_snapshot)
  → worker (handlers.py) đọc project_id từ execution snapshot
    (KHÔNG còn fallback "lấy project đầu tiên")
  → guard PROJECT_TEAM_OPERATING_PROFILES (đã có, handlers.py:228)
    verify authority thật qua ProjectTeamClient.get_run_authority
```

Bug thực chất không phải "thiếu guard" — guard fail-closed đã đúng cho
15/16 profile. Bug là pipeline schedule chưa từng truyền `project_id` thật
tới guard đó: với "operations" nó bị fallback ghi đè bằng project sai; với
các profile khác, guard chặn đúng nhưng khiến schedule không dùng được. Fix
này vá lỗ hổng (operations) và đồng thời làm schedule mọi profile hoạt động
đúng như thiết kế.

**Phạm vi áp dụng:** `project_id` bắt buộc cho **tất cả** `agent_profile` khi
tạo schedule (không giới hạn ở "operations"), khớp với việc guard runtime
vốn đã áp dụng cho 15/16 profile.

## Data model & Migration

Migration Expand-only (CLAUDE.md Encore Guardrail #4 — release chỉ Expand).

**`services/cosa/storage/control-plane-schema.ts`:**

- `workspaceScheduleDefinitions`: thêm `projectId: text("project_id")`
  (nullable ở schema — migration Expand không backfill NOT NULL an toàn
  trong 1 bước) + `isLegacyUnscoped: boolean("is_legacy_unscoped")
  .default(false).notNull()`.
- `workspaceScheduleExecutions`: thêm `projectIdSnapshot: text(
  "project_id_snapshot")` — snapshot tại thời điểm dispatch, cùng nguyên
  tắc với `promptTemplateSnapshot`/`agentProfileSnapshot` đã có.

**Backfill (migration nối tiếp ngay sau, hoặc cùng migration):**

- Mỗi `workspaceScheduleDefinitions` có `projectId IS NULL`: gọi
  `services/company` lấy project đầu tiên (`id` giảm dần — giữ đúng hành vi
  cũ) của `workspaceId`, set `projectId` = project đó,
  `isLegacyUnscoped = true`.
- Nếu workspace không còn project nào: set `state = 'disabled'` cho
  definition đó — không được để nó tiếp tục dispatch execution với
  `project_id NULL`.
- Sau backfill, tầng ứng dụng coi `projectId` là bắt buộc logic dù cột DB
  vẫn nullable ở schema (tránh 1 migration NOT NULL rủi ro trên bảng đang có
  dữ liệu) — mọi insert mới phải có giá trị, validate ở
  `createScheduleEndpoint`.

**API contract (`services/cosa`):**

- `CreateScheduleParams` (`workspace-schedule.handler.ts`) thêm
  `projectId: string` bắt buộc (không còn optional).
- `createWorkspaceSchedule`: reject nếu `projectId` rỗng →
  `APIError.invalidArgument`.
- Dispatcher (khu vực tạo execution trong `workspace-schedule.service.ts`)
  copy `def.projectId` → `execution.projectIdSnapshot` khi insert.

**`apps/cosa/api/schedule_routes.py`:**

- Request body tạo schedule thêm `project_id: str` bắt buộc (Pydantic, không
  `Optional`).
- Gọi `verify_project_context(plane, identity, project_id)` trước khi
  forward sang `services/cosa` — fail 422/404 sớm nếu project không thuộc
  workspace hoặc không active.
- Forward `project_id` trong payload proxy.

**`apps/cosa/worker/handlers.py`:**

- Xóa `_resolve_workspace_project_id` (dòng 63) và đoạn đặc cách
  `agent_profile == "operations"` ở dòng 1155 — không còn fallback "lấy
  project đầu tiên" ở bất kỳ đâu trong runtime.
- Đọc `project_id` trực tiếp từ execution snapshot
  (`data.get("projectIdSnapshot")`), gán vào `run_payload["project_id"]`.
- Nếu snapshot thiếu `project_id` (chỉ có thể do row `is_legacy_unscoped`
  chưa kịp backfill hoặc lỗi dữ liệu) → fail closed với lỗi mới
  `schedule_project_context_missing`, tách biệt khỏi guard chung
  `project_context_required` để phân biệt nguyên nhân trong log/alert.

## Error handling & Runtime authority flow

| Trạng thái | Khi nào | Xử lý |
|---|---|---|
| `invalidArgument` (services/cosa) | Tạo schedule thiếu `projectId` | 400 tại API tạo, không insert |
| `PROJECT_NOT_FOUND_OR_FORBIDDEN` (apps/cosa, có sẵn) | `project_id` không thuộc workspace/không active | 404 tại lúc tạo, trước khi forward |
| `schedule_project_context_missing` (mới) | Execution snapshot thiếu `project_id_snapshot` | Fail execution, log rõ nguyên nhân, không disable definition (có thể lỗi tạm) |
| `project_team_authority_denied` (có sẵn, handlers.py:254) | Project bị xóa/archive hoặc profile không có authority tại thời điểm chạy | Fail execution — cơ chế fail-closed có sẵn, nay nhận đúng `project_id` |
| `isLegacyUnscoped = true` | Schedule được backfill từ dữ liệu cũ | Không chặn chạy — chỉ là flag để Founder Hub cảnh báo "gán project tự động, hãy xác nhận lại". UI nằm ngoài phạm vi spec backend này. |

**Thứ tự guard tại runtime** (không đổi thứ tự đã có, chỉ đổi nguồn
`project_id`):

1. Reject sớm nếu thiếu `workspace_id`/`project_id`
   (`project_context_required`) — không còn bị "lấp đầy" bởi fallback sai.
2. Re-check `project_id` khớp `ConversationRecord` đã lưu (defense-in-depth
   có sẵn, dòng 190-226) — giữ nguyên.
3. Guard `PROJECT_TEAM_OPERATING_PROFILES` gọi `get_run_authority` —
   fail-closed thật khi project bị xóa. Giữ nguyên logic, chỉ input đúng
   hơn.
4. Chỉ sau khi qua cả 3 bước mới chạm kernel. `ConversationRecord`/
   `MessageRecord` (role=`user`) được tạo trước guard, nhưng kernel (run
   thật, có thể sinh side effect) chỉ chạy sau — cần test xác nhận thứ tự
   này, đúng yêu cầu "authority phải chặn trước kernel và không có side
   effect".

Không có cơ chế tự phục hồi ngầm: execution fail vì lý do project-liên-quan
không tự thử lại với project khác. Retry hiện có
(`workspace-schedule.service.ts`, ~dòng 120-146) chỉ retry cùng
execution/snapshot, không đổi `project_id`.

## Testing

**Unit/integration** (`make services-test-cosa`, `make agent-test` — không
cần Postgres disposable):

1. `services/cosa`:
   - `createWorkspaceSchedule` reject khi thiếu `projectId`.
   - Dispatcher copy đúng `def.projectId` → `execution.projectIdSnapshot`.
   - Migration backfill: workspace không còn project nào → definition
     chuyển `disabled`, không chỉ set `isLegacyUnscoped`.

2. `apps/cosa`:
   - `schedule_routes.py`: thiếu `project_id` → 422 tại tầng Pydantic.
   - `project_id` không thuộc workspace → 404
     `PROJECT_NOT_FOUND_OR_FORBIDDEN`, không forward sang `services/cosa`
     (assert mock client không bị gọi).
   - `handlers.py` scheduled-execution: snapshot thiếu `project_id_snapshot`
     → fail `schedule_project_context_missing`; assert
     `_resolve_workspace_project_id` không còn tồn tại trong module.
   - Test thứ tự guard: fixture run có `project_id` hợp lệ nhưng
     `ProjectTeamClient.get_run_authority` mock trả lỗi → assert
     `run_kernel` không được gọi, và không có `MessageRecord` role=
     `assistant` nào được tạo (không có side effect từ kernel).

**E2E hai Project** (`make e2e-cross-plane-smoke` — cần Postgres disposable
+ Encore CLI):

- Setup: 1 workspace, 2 Project (A, B). Schedule gắn cứng Project A.
- Retry: fail rồi retry execution → assert timeline/activity vẫn ghi vào
  Project A, không lệch sang B.
- Revoke: archive Project A giữa chừng → assert execution kế tiếp
  fail-closed (`project_team_authority_denied`), không tự chuyển sang B.
- Đổi thứ tự Project: tạo Project B trước rồi mới tạo Project A (đảo ngược
  thứ tự "id giảm dần" mà fallback cũ từng dựa vào) → assert schedule vẫn
  chạy đúng Project A đã gắn.

**Không cần test mới:** fail-closed ở tầng `ProjectTeamClient` (đã có test
hiện hữu, chỉ input thay đổi) — chỉ cần đảm bảo test hiện có vẫn xanh.

## Ngoài phạm vi (out of scope)

- UI Founder Hub hiển thị badge `isLegacyUnscoped` / chọn Project khi tạo
  schedule — Flutter chưa wire API tạo schedule (stub "removed from Founder
  Trial R1 contract"); việc khôi phục UI này là quyết định sản phẩm riêng,
  thuộc sub-project #4 (Hub Workforce API) trong đợt audit này.
- Validate/whitelist giá trị `agentProfile` tại `services/cosa` (hiện là
  free-text, không enum-check) — phát hiện trong quá trình điều tra nhưng
  không phải nguyên nhân của bug Project-scope, để lại cho một fix riêng
  nếu cần.
