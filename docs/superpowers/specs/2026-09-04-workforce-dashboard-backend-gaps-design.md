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

**Nguồn dữ liệu:** registry thật — 5 `AgentSpec` hard-code trong
`apps/cosa/agents/specs.py` (`operations`, `finance`, `marketing`,
`customer_support`, `customer_support_autopilot`), đọc qua
`SpecResolver`/`plane.spec_registry` giống cách `worker/run_core.py` resolve
spec (không tin object Python import trực tiếp, theo rule đã ghi ở CLAUDE.md).

**⚠️ Thay đổi hiển thị có chủ đích:** FE hiện fallback về `default12Agents` —
12 agent hư cấu hard-code (`founder_copilot`, `general`, ...) không khớp
registry thật. Sau phase này, Founder Dashboard hiển thị **5 agent thật**
thay vì 12 agent giả. Đây là sửa đúng (rule 7 — không dữ liệu giả), không phải
side-effect ngoài ý muốn.

**Field mapping** (response `WorkforceRosterEntryOut`):

| Field FE cần | Nguồn | Ghi chú |
|---|---|---|
| `id` | index tự sinh (int, ổn định theo thứ tự alphabet `spec.id`) | Không có id số nguyên tự nhiên trong `AgentSpec` |
| `key` | `spec.id` | vd. `"operations"` |
| `name` | bảng tĩnh `_DISPLAY_NAME[spec.id]` | Viết tay 5 dòng, không suy diễn từ `id` |
| `role_title` | `spec.instructions` (nguyên văn, đã là 1 câu ngắn) | |
| `department` | bảng tĩnh `_DEPARTMENT[spec.id]` | vd. `operations`→`"Operations"`, `finance`→`"Finance & Legal"` |
| `agent_type` | hằng số `"specialist"` | Không có khái niệm `orchestrator` trong registry thật hiện tại |
| `default_model_profile` | hằng số `"reasoning"` | Model routing thật nằm ở LiteLLM config, không per-agent-display |
| `risk_level` | map từ `autonomy_level`: L0→1, L1→2, L2→3 | |
| `status` | hằng số `"idle"` | Chưa có tracking trạng thái runtime per-agent (khác trạng thái per-run) |
| `enabled` | hằng số `true` | Mọi spec trong registry mặc định coi là enabled |

## Phase 2 — Work products (workspace-wide)

**Route:** `GET /agent/workforce/artifacts?limit=`

**Thêm method mới** `ArtifactRepository.list_for_workspace(workspace_id, limit)`
(hiện chỉ có `list_for_conversation`) — cả `PostgresArtifactRepository` lẫn
`InMemoryArtifactRepository`. Query: join `agent.workspace_artifacts` với
runs cùng `workspace_id`, sắp theo `created_at desc`.

**Field mapping** (response `WorkforceWorkProductOut`):

| Field FE cần | Nguồn | Ghi chú |
|---|---|---|
| `id` | `artifact_id` | |
| `title` | `ArtifactRecord.name` | |
| `product_type` | `ArtifactRecord.media_type` | |
| `status` | hằng số `"READY"` | Chưa có workflow DRAFT/REVIEW/APPROVED nào tồn tại ở tầng artifact — bịa ra sẽ sai (rule 7) |
| `author_agent_key` | suy từ `ArtifactRecord.spec_identity` (nếu có) hoặc `creator_principal` | |
| `content_markdown` / `summary` | **KHÔNG trả trong MVP** — trả `storage_uri` để FE tự fetch/hiển thị link | Xem "Known gap" dưới |

**Known gap (ghi rõ, không che):** `work_product_inspector_modal.dart` đang
đọc `content_markdown` để hiển thị nội dung inline trong modal — MVP phase
này **không** cung cấp field đó (cần thêm storage-fetch adapter, ngoài phạm
vi). FE cần fallback hiển thị "Xem file gốc" (link `storage_uri`) khi
`content_markdown` vắng mặt, thay vì hiển thị trống trơn.

## Phase 3 — Stage roster P0–P6

**Route:** `GET /agent/workforce/stage-roster/{stage_code}`

Cross-plane: `apps/cosa` gọi HTTP sang `services/company` (route mới,
`expose: false`, xác thực bằng `COSA_COMPANY_DELEGATION_SECRET` — đúng secret
đã có cho chiều apps/cosa→company, xem CLAUDE.md mục "3 secret cross-plane").
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
