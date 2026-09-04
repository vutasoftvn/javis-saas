# Workforce Dashboard — vá 4+1 endpoint chưa từng có backend

**Ngày:** 2026-09-04
**Bối cảnh:** `docs/architecture/frontend-api-migration-register.md` (2026-09-02) đã
audit và liệt kê 9 nhóm method trong `AgentPlatformService`/`AgentsService` gọi
route backend **không tồn tại** (`unknown — BLOCKS RELEASE`). Spec này chỉ giải
quyết 5 trong 9 nhóm đó — nhóm còn lại (`decisions`, `heartbeats/routines`,
`budgets/cost-ledger`, agent/tool/skill CRUD) bị loại vì tài liệu ghi "không xác
nhận UI gọi" (khả năng code chết) — không xây backend cho UI chưa chắc ai chạm
tới.

## Phạm vi (5 phase, theo thứ tự build)

1. Agents roster (read)
2. Work products — workspace-wide (read)
3. Stage roster P0–P6 (read)
4. Dashboard summary (aggregator, read)
5. Escalations list — **chỉ đọc, không có resolve** (read)

**Loại khỏi phạm vi lần này:** `resolveEscalation` (action tài chính/quyền —
`force_approve`/`increase_budget`/`block_permanently`) — theo đúng cảnh báo của
tài liệu audit, domain tier/action escalation cần một phiên thiết kế riêng
trước khi cho phép Founder bấm hành động rủi ro cao (CLAUDE.md quy tắc 8). Nút
"Resolve" trên FE phải bị ẩn/disable trong khi domain chưa có, không được hiện
ra rồi âm thầm không làm gì.

## Nguyên tắc chung cho cả 5 phase

- Không tạo bảng Postgres mới ở bất kỳ phase nào — mọi nguồn dữ liệu đã tồn
  tại (registry `AgentSpec`, `ArtifactRepository`, `project_operating_setups`,
  `workforce.run.list`). Nếu một phase cần bảng mới, đó là dấu hiệu thiết kế
  sai — quay lại xem xét.
- Route mount ở `apps/cosa/api/workforce_routes.py` (prefix `/agent/workforce`,
  đã có `router` sẵn) — nối tiếp đúng convention Task 7 đã dùng cho
  approvals/org-chart/runs.
- Field nào không có nguồn dữ liệu thật (vd. `status` per-agent, `status`
  work-product) → set **hằng số cố định** kèm comment giải thích rõ, KHÔNG suy
  diễn/bịa giá trị động trông như thật (rule 7: "Trạng thái ứng dụng phải
  structured, không suy diễn").
- Mỗi phase: thêm `MvpEndpoint` tương ứng vào `shared/contracts/mvp-surface.json`
  → regenerate `mvp_endpoints.g.dart` + `mvp_contracts_generated.py` → migrate
  đúng method đó trong `AgentPlatformService` sang gọi qua
  `WorkforceMvpService`/`MvpRequestClient` (bỏ hẳn cách gọi `ApiClient.get`
  thô hiện tại) — đúng pattern Task 7 đã làm cho approvals/org-chart.

## Phase 1 — Agents roster

**Route:** `GET /agent/workforce/roster`

**Nguồn dữ liệu (sửa sau khi đọc code kỹ hơn — tốt hơn phương án ban đầu):**
KHÔNG dùng 5 `AgentSpec` thô trong `apps/cosa/agents/specs.py` như phác thảo
đầu tiên. Đã có sẵn `FUNCTIONAL_AGENT_CATALOG`
(`packages/agent/workforce/catalog.py`, 6 entry: `cashflow_planner`,
`accounting_document_specialist`, `market_research_specialist`,
`campaign_planner`, `compliance_analyst`, `founder_office_orchestrator`) +
route `GET /agent/workforce/composition` đã mount thật
(`workforce_routes.py:186`), trả `WorkforceCompositionEntry` với đúng
`title`/`description`/`default_department` + trạng thái **assignment thật**
theo từng workspace (`assigned: bool`, `status` từ `WorkforceAssignmentRecord`)
— dữ liệu sống hơn nhiều so với spec tĩnh. Tái dùng nguồn này đúng rule 4
("không nhân bản kiến trúc — tìm trong repo trước").

**⚠️ Thay đổi hiển thị có chủ đích:** FE hiện fallback về `default12Agents` —
12 agent hư cấu hard-code (`founder_copilot`, `general`, ...) không khớp bất
kỳ nguồn thật nào. Sau phase này, Founder Dashboard hiển thị **6 functional
agent thật** (từ catalog + trạng thái assignment thật) thay vì 12 agent giả.
Đây là sửa đúng (rule 7 — không dữ liệu giả), không phải side-effect ngoài ý
muốn.

**Field mapping** (response `WorkforceRosterEntryOut`, route mới
`GET /agent/workforce/roster` gọi lại đúng logic `get_composition()` rồi
reshape — không sửa route `/composition` đang có consumer khác):

| Field FE cần | Nguồn | Ghi chú |
|---|---|---|
| `id` | index tự sinh (int, ổn định theo thứ tự `FUNCTIONAL_AGENT_CATALOG` khai báo) | Không có id số nguyên tự nhiên trong catalog |
| `key` | `entry.functional_key` | vd. `"cashflow_planner"` |
| `name` | `entry.title` | vd. `"Cashflow Planner"` |
| `role_title` | `entry.description` | Câu mô tả ngắn có sẵn |
| `department` | `entry.default_department` | Có sẵn, thật (vd. `"Finance"`) |
| `agent_type` | hằng số `"specialist"` | Catalog không phân loại orchestrator/specialist — mọi entry hiện tại đều dạng propose/human-accept |
| `default_model_profile` | hằng số `"reasoning"` | Model routing thật nằm ở LiteLLM config, không per-agent-display |
| `risk_level` | hằng số `2` (medium) | `FunctionalAgentEntry` không có `autonomy_level` field — mọi entry hiện tại đều dạng "đề xuất, không tự thực thi" |
| `status` | `"active"` nếu `assigned=True`, ngược lại `"available"` | **Dữ liệu thật** từ `WorkforceAssignmentRecord.status` qua `repo.list_assignments()` — không phải hằng số |
| `enabled` | hằng số `true` | Mọi entry trong catalog coi là khả dụng để assign |

## Phase 2 — Work products (workspace-wide)

**Route:** `GET /agent/workforce/artifacts?limit=`

**Sửa lại nguồn dữ liệu chính xác (đã đọc code thật):** model đúng là
`agent.artifacts.models.WorkspaceArtifact` (bảng
`agent_artifact.workspace_artifacts`), KHÔNG phải `ArtifactRecord` trong
`artifacts/lifecycle.py` như phác thảo ban đầu (đó là 1 class khác, không
được `plane.artifact_repository` dùng). Thêm method mới
`ArtifactRepository.list_for_workspace(workspace_id, limit)` (hiện chỉ có
`list_for_conversation`) — cả `PostgresArtifactRepository` (query trực tiếp
theo `workspace_id`, bỏ điều kiện `conversation_id`) lẫn
`InMemoryArtifactRepository`, sắp theo `created_at desc`.

**Field mapping** (response `WorkforceWorkProductOut`):

| Field FE cần | Nguồn | Ghi chú |
|---|---|---|
| `id` | `artifact.artifact_id` | |
| `title` | `artifact.display_name` | Field thật, không phải `name` |
| `product_type` | `artifact.media_type` | |
| `status` | `artifact.status` (`available`/`failed`/`archived`) map sang `"READY"`/`"FAILED"`/`"ARCHIVED"` | **Dữ liệu thật**, không phải hằng số — sửa so với phác thảo ban đầu (không có workflow DRAFT/REVIEW nhưng CÓ status thật ở tầng lifecycle) |
| `author_agent_key` | tra `artifact.run_id` trong map `{run_id: agent_spec_id}` dựng 1 lần từ `plane.repository.list_runs()` cùng request (tránh N+1) | Fallback `"unknown"` nếu `run_id` rỗng hoặc không có trong danh sách run gần đây (giới hạn bởi `limit` của `list_runs`) |
| `content_markdown` / `summary` | **KHÔNG trả trong MVP** — trả `object_ref` để FE tự fetch/hiển thị link | Xem "Known gap" dưới |

**Known gap (ghi rõ, không che):** `work_product_inspector_modal.dart` đang
đọc `content_markdown` để hiển thị nội dung inline trong modal — MVP phase
này **không** cung cấp field đó (cần thêm storage-fetch adapter, ngoài phạm
vi). FE cần fallback hiển thị "Xem file gốc" (link `object_ref`) khi
`content_markdown` vắng mặt, thay vì hiển thị trống trơn.

## Phase 3 — Stage roster P0–P6

**Route:** `GET /agent/workforce/stage-roster/{stage_code}`

Cross-plane: `apps/cosa` gọi HTTP sang `services/company` (route mới trong
`operations/handlers/task.handler.ts`). Sửa so với phác thảo ban đầu sau khi
đọc pattern thật đang dùng cho các route apps/cosa→company khác
(`listAgentClaimableTasks`, cùng file): route đó `expose: true` nhưng biên
giới bảo mật thật là `resolveCosaTaskContext(authorization, {workspaceId,
capabilityId})` — verify delegation JWT ký bởi `COSA_COMPANY_DELEGATION_SECRET`
(`shared/auth/cosa-task-delegation.ts`), không phải `expose: false` ở tầng
network. Route mới dùng đúng pattern này, tái dùng capability đã có sẵn
`WGA_CAP_TASK_LIST` (`operations.task.list`) — không cần capability mới.
Company đọc `strategy.project_operating_setups` lọc theo `selected_stage =
stage_code` + `workspace_id`, lấy `project_id` các dự án đang ở stage đó rồi
join `operating.task_projects` → `operating.tasks` (đã xác nhận schema thật
qua `psql \d`, không phải `operations.tasks` như phỏng đoán ban đầu).

**Field mapping** (response `WorkforceStageRosterOut`):

| Field FE cần | Nguồn |
|---|---|
| `stage` (meta: `stage_code`, `stage_name_vi`) | hằng số tra bảng P0–P6 → tên tiếng Việt (đã có ở FE, chỉ cần đối chiếu) |
| `roster` (list task trong stage) | `strategy.project_operating_setups` (lọc `selected_stage`) → `operating.task_projects` → `operating.tasks` |
| `summary.total` | đếm roster |
| `summary.high_priority` / `medium` | `operating.tasks.priority` (cột `text`, default `'medium'`, đã xác nhận tồn tại) |
| `summary.locked` | task thuộc project có `project_operating_setups.status != 'IN_PROGRESS'` (chưa tới lượt active) — định nghĩa tạm, ghi rõ trong code comment |

## Phase 4 — Dashboard summary

**Route:** `GET /agent/workforce/dashboard-summary`

Aggregator thuần — gọi lại (trong-process, không qua HTTP) các hàm đã có:
`list_approvals` (pending count), `list_runs` (active/failed count),
`get_composition`, `get_health`, cộng thêm kết quả Phase 1–3 nếu cần số liệu
tổng. Không logic nghiệp vụ mới, không bảng mới — chỉ gộp response đã có sẵn
thành 1 object.

## Phase 5 — Escalations list (read-only)

**Route:** `GET /agent/workforce/exceptions?status=OPEN`

**Định nghĩa MVP của "escalation":** run có `RunStatus.FAILED` trong workspace
(đã có sẵn qua `plane.repository`, cùng nguồn `workforce.run.list` dùng).
KHÔNG tạo bảng/domain exception mới.

**Field mapping** (response `WorkforceExceptionOut`):

| Field FE cần | Nguồn | Ghi chú |
|---|---|---|
| `id` | `run_id` | |
| `exception_type` | hằng số `"run_failed"` | MVP chỉ có 1 loại — mọi phân loại chi tiết hơn cần domain design riêng |
| `tier` | hằng số `"LEAD_NOTIFY"` | **Không tự gán `FOUNDER_GATE`** — đó là phân loại rủi ro, để trống cho phiên thiết kế escalation riêng quyết định |
| `status` | `"OPEN"` cố định (mọi FAILED run coi là chưa xử lý) | |
| `founder_gate_count` (summary) | luôn `0` | Không có FOUNDER_GATE trong MVP này |

**FE phải sửa kèm:** ẩn/disable nút "Resolve" trong
`exception_escalation_inbox.dart` — action `resolveEscalation` KHÔNG được gọi
tới backend nào (giữ nguyên tình trạng ngày hôm nay: không hoạt động), nhưng
nút không được hiện disable trong khi trông như còn hoạt động, tránh đúng rủi
ro tài liệu audit đã cảnh báo (CLAUDE.md quy tắc 8).

## Ngoài phạm vi (rõ ràng, không tự làm thêm)

- `resolveEscalation` và toàn bộ domain tier/action escalation thật.
- `decisions`, `heartbeats/routines`, `budgets/cost-ledger`, agent/tool/skill
  CRUD — chưa xác nhận có UI sống nào gọi tới.
- Nội dung inline (`content_markdown`) cho work product — cần storage-fetch
  adapter riêng.

## Testing

Mỗi phase: 1 test Python cho route mới (`tests/apps/cosa/...`, theo pattern
`test_kickoff_suggestion_route.py`), 1 test Dart cho method
`AgentPlatformService`/`WorkforceMvpService` migrate sang (theo pattern
`agent_platform_service_test.dart` — assert path `/agent/workforce/...` +
xử lý `ApiFailure`, không nuốt lỗi thành list rỗng).
