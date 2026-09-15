# Design Amendment: Đóng vòng đúng đắn cho Workspace, Project, OKR, Weekly, Task và Executive Board

**Ngày:** 2026-09-14
**Trạng thái:** REVISED theo định hướng Founder — chưa là ủy quyền triển khai code
**Thay đổi đối với:** `2026-09-14-workspace-project-okr-weekly-executive-board-foundation-design.md`

## Vấn đề cần sửa

Đợt triển khai foundation trước đã đưa lifecycle UI, OKR routes, generator
OKR-to-Weekly và Workspace Executive Board vào code. Kiểm tra lại source cho
thấy bốn khoảng trống làm hệ thống chưa thể được xem là truthful hoặc kín scope:

1. `ProjectOperatingLoop` backend và Flutter dùng hai JSON shape khác nhau;
   UI có thể hiển thị rỗng/sai dù dữ liệu thật tồn tại.
2. Task legacy còn suy diễn Project đầu tiên khi thiếu `projectId`; route đổi
   trạng thái trong Operating Loop chỉ xác minh Project trên URL, không khoá
   `task.project_id` theo Project đó.
3. Cycle có `currentWeek` nhưng chưa có command CAS để đóng tuần, sang tuần,
   hoàn tất cycle và ghi audit.
4. `workspace_executive_role_activations` thể hiện office được bật cho công ty,
   nhưng UI đang chiếu trạng thái đó thành “role active trong mọi Project”,
   thay vì phân biệt Workspace office với Project Agent deployment đang chạy.

## Quyết định kiến trúc đề xuất

### 1. Một đường vận hành chuẩn, Project-scoped

Canonical read/write cho Operating Loop là
`/operations/projects/:projectId/operating-loop/*`. JSON từ
`getProjectOperatingLoop` là contract duy nhất của màn hình Project. Flutter
phải giải mã đúng wrapper `objectives[].objective`,
`objectives[].keyResults[].keyResult`, `currentWeek`, `commitments` và `tasks`;
backend không flatten DTO chỉ để phù hợp một client cũ.

`modules/strategy/okr_service.dart` có thể tiếp tục tồn tại cho các màn hình
OKR tổng quát đã có, nhưng không được trở thành đường ghi song song cho Project
Operating Loop. Không có UI nào được hiển thị evidence/decision như dữ liệu của
Operating Loop nếu endpoint canonical không trả chúng.

### 2. Project là bắt buộc với mọi business write, nhưng onboarding được chọn baseline

Mọi Task create/proposal/status/schedule/claim có business effect phải nhận
`projectId` rõ ràng. `workspace_id` chỉ là tenant boundary, không được dùng để
suy diễn hoặc thay thế Project. Query/UPDATE theo task ID phải luôn gồm
`workspace_id` và `project_id`; association commitment/initiative/weekly plan
phải thuộc cùng cặp đó.

Project tạo mới có hai mode rõ ràng:

```text
NEW               -> mặc định P0_DISCOVERY
ONBOARD_EXISTING  -> Founder/co-founder chọn P0…P6 và nhập initialization rationale
```

`ONBOARD_EXISTING` tạo baseline lần đầu trong cùng transaction: Project được
insert tại stage Founder đã chọn, `stageVersion = 1`, và event
`PROJECT_INITIALIZED` có `fromStage = null`, `toStage = initialStage`,
`initializationSource = FOUNDER_ONBOARDING`. Đây không phải transition và
không bịa chuỗi P0→…→Pn. Sau baseline đầu tiên, mọi đổi stage dùng lifecycle
transition CAS: tiến một bậc, rollback có rationale, stale version không ghi
event. Project đã có lifecycle event hoặc operational work không được dùng lại
onboarding mode để viết lại lịch sử.

### 3. Weekly là state machine thủ công, không phải lịch

Cycle tạo ra đầy đủ các Week skeleton 1..N trong cùng transaction. Founder
đóng tuần hiện tại với review có cấu trúc; server dùng `expectedCurrentWeek`
CAS để ghi review, append event và chỉ sau đó chuyển `current_week`. Khi đóng
tuần N, cycle chuyển `COMPLETED`; không tự đổi lifecycle Project hay tự tạo
commitment/task. Mọi retry stale thất bại trước khi có event.

### 4. Một Role/Office thuộc Workspace; Project chỉ deploy Agent/Skill scoped

Role catalog built-in thuộc Platform; nếu sau này Founder clone/customize thì
clone đó là Workspace asset. `workspace_executive_role_activations` là
**office availability/kill switch** của Workspace: công ty có một CFO/CMO/COO,
không có bản sao Role theo Project. `project_executive_role_activations` cũ
tiếp tục deprecated và không được hồi sinh làm authority mới.

Project không sở hữu Role. Project chỉ deploy `workspace_agent` hiện hữu qua
`project_agent_deployments`, tại đó Project thu hẹp data scope, budget và
capability policy. Một Workspace role có thể tư vấn một Project khi đồng thời:

```text
workspace office ACTIVE
AND Project có ACTIVE project_agent_deployment cho required agent profile
AND role được stage policy cho phép ở Project hiện tại
AND deployment resolve đúng Workspace Agent/AgentSpec hash
AND required skill pins resolve đúng version/hash
```

`project_agent_deployments` và `workspace_agents` đã là path V2 cho exact
deployment authority; dùng `resolveProjectAgentAuthorityV2`, không tạo bảng
Project Role song song. `frameDeliberation` và worker authority tái kiểm tra
office state, Project deployment, stage policy và pins lúc dùng; role chỉ
advisory (`L1_PROPOSE`) và không nhận effectful capability. Stage suggestion
chỉ gợi ý: “bật office ở Workspace” hoặc “deploy agent vào Project”; server
enforce stage policy ở frame/run, không auto-activate hay auto-deploy.

### 5. Contract generation phải deterministic

`gen-startup-team-profiles.mjs` phải sinh Python đã tương thích định dạng ruff.
Sau `generate -> format check -> generate --check`, file generated không được
đổi. Generated files chỉ được cập nhật bằng generator, không sửa tay.

## Giới hạn

- Không nối Skill mới vào workflow/tool. Existing required skill pins chỉ là
  điều kiện resolve fail-closed của Workspace Agent deployment/deliberation.
- Không xoá bảng activation cũ, route cũ hay dữ liệu trong đợt này. Chỉ thêm
  migration compatible, chuyển callers và deprecate có thông báo rõ ràng.
- Không auto-transition lifecycle, auto-bind role, auto-create commitment hay
  auto-approve work.

## Điều kiện thành công

Một Workspace có hai Project phải chứng minh được bằng PostgreSQL/process E2E:

- Task/commitment/initiative/role của Project A không thể đọc hoặc đổi qua URL
  hay command của Project B;
- transition stage stale, advance week stale và Workspace office mutation stale
  không ghi event;
- Flutter hiển thị đúng payload backend thật cho Objective/KR/Initiative,
  current Week, commitment và task;
- Workspace office ACTIVE một mình không cho role chạy deliberation ở Project
  chưa có ACTIVE agent deployment hoặc không đúng stage;
- `make contracts-check`, focused tests, `make verify` và
  `make e2e-cross-plane-smoke` xanh trên trạng thái migration mới.
