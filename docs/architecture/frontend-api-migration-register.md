# Frontend API Migration Register

Nguồn: `docs/architecture/generated/route-inventory.md` (sinh bởi
`python scripts/route_inventory.py`) tại thời điểm 2026-09-02, đối chiếu trực
tiếp với các router thật sự được `include_router()` trong
`apps/cosa/api/app.py` (không suy diễn từ tên file router).

**Cập nhật 2026-09-04** — plan
`docs/superpowers/plans/2026-09-04-workforce-dashboard-backend-gaps.md` +
follow-up ngay sau đó đã đóng 5 route `unknown — BLOCKS RELEASE` bên dưới
(agents roster list, dashboard-summary — riêng `AgentPlatformService`, work
products list, stage roster get, escalations list read-only). Các dòng liên
quan đã cập nhật trạng thái `canonical` kèm ngày đóng; phần mutation
(`resolveEscalation`, `acceptWorkProduct`, `requestWorkProductRevision`,
`checkAgentStageFit`) và `AgentsService.getDashboardSummary` (method riêng
biệt, khác `AgentPlatformService.getDashboardSummary` — KHÔNG được migrate
trong đợt này) vẫn `unknown`, được tách thành dòng riêng để không lẫn với
phần đã đóng.

Phạm vi: các route ACTIVE (đang được một consumer sống — controller/mixin
thực sự gọi từ UI, không phải chỉ tồn tại trong file service) trong domain
Agents (`frontend/lib/modules/agents/services/agent_platform_service.dart`,
`frontend/lib/modules/agents/services/agents_service.dart`) và route
Approvals liên quan trực tiếp. Route lịch sử/đã chết hoàn toàn (không còn file
nào import) không liệt kê ở đây — xem `rg -n "✗ GHOST"
docs/architecture/generated/route-inventory.md` cho danh sách đầy đủ toàn bộ
frontend.

Phân loại:
- `canonical` — route hiện tại khớp đúng backend đang mount, không cần sửa.
- `migration-needed` — có route canonical thay thế đã xác nhận tồn tại và
  mounted; cần trỏ frontend sang route đó.
- `intentionally-unsupported` — tính năng đã xác nhận bị rút/không triển khai,
  có quyết định kiến trúc ghi lại.
- `unknown` — **không tìm thấy route backend nào khớp** (đã grep toàn bộ
  `apps/cosa/api/*.py`) và cũng không có ghi nhận kiến trúc nào nói tính năng
  này bị rút. Với mutation người dùng có thể chạm tới trên Dashboard, đây là
  **blocker phát hành** — không được suy diễn thành `intentionally-unsupported`
  chỉ vì tiện.

## Approvals (Founder Command Center)

| Frontend method | Route cũ (frontend gọi) | Route thật đã mount | Trạng thái | Consumer sống | Ghi chú |
|---|---|---|---|---|---|
| `AgentPlatformService.listApprovals` | `GET /workforce/approvals` (thiếu `/agent`, rơi vào Encore company :4000, luôn 404) | `GET /agent/workforce/approvals` (`apps/cosa/api/workforce_routes.py`, mount qua `workforce_router` tại `app.py:200`) | **canonical (đã sửa Task 7)** | `hub_control_plane_mixin.dart:101` (Founder Dashboard) | Đã migrate sang `WorkforceMvpService.listApprovals` trong commit này. |
| `AgentPlatformService.approveRequest` / `rejectRequest` | `POST /workforce/approvals/{id}/approve` / `/reject` (route con không tồn tại ở backend thật lẫn cũ) | `POST /agent/workforce/approvals/{id}/decision` (body `{approved: bool, reason}`) | **canonical (đã sửa Task 7)** | `hub_control_plane_mixin.dart:202,212` | Backend chỉ có MỘT endpoint decision hợp nhất, không có 2 route con riêng — đã map đúng cờ `approved`. |
| `modules/approvals/services/approvals_service.dart` — `list`/`decide` | — | `GET /agent/workforce/approvals`, `POST /agent/workforce/approvals/{id}/decision` | canonical (Task 6 đã sửa) | `ApprovalsController` | Ngoài phạm vi file Task 7; đã đúng từ trước. |
| `modules/approvals/services/approvals_service.dart` — `getApprovalsList`/`getApprovals`/`approve`/`reject`/`requestRevision`/`approveStep`/`rejectStep` | `GET/POST /agent/approvals...` | Không mounted — `apps/cosa/api/approval_routes.py` có `deprecated=True` nhưng KHÔNG được `include_router()` trong `apps/cosa/api/app.py` | **migration-needed (dead code, chưa xoá)** | Không tìm thấy call site nào còn dùng các method này (đã `rg` toàn repo) | Nợ kỹ thuật để lại từ Task 6, ngoài phạm vi file Task 7 (không nằm trong danh sách file được sửa) — ghi nhận, không tự ý xoá file người khác đang sở hữu. |

## Agents domain — org chart & runs

| Frontend method | Route cũ | Route thật đã mount | Trạng thái | Consumer sống | Ghi chú |
|---|---|---|---|---|---|
| `AgentPlatformService.getOrgChart` / `AgentsService.getOrgChart` | `GET /workforce/org-chart` | `GET /agent/workforce/org-chart` | **canonical (đã sửa Task 7)** | `hub_control_plane_mixin.dart` gián tiếp qua `agentPlatformService`; `agents_controller.dart:67` | Đã thêm `WorkforceMvpService.getOrgChart()` (model tự do `Map<String,dynamic>` — backend trả cây phân cấp, chưa có schema cố định). |
| `AgentsService.getRuns` | `GET /workforce/runs?agent_key=&status=&limit=&offset=` | `GET /agent/workforce/runs?limit=` | **canonical (đã sửa Task 7)** | `agents_controller.dart:80` | Backend thật (`workforce_routes.py:list_runs`) chỉ đọc `limit`; `agent_key`/`status`/`offset` không được server hỗ trợ — giữ tham số trong chữ ký Dart để không phá call site, nhưng không còn giả vờ gửi filter server không đọc. |
| `AgentsService.getRunDetail` | `GET /workforce/runs/{id}` | `GET /agent/workforce/runs/{id}` | `migration-needed` (chưa sửa trong commit này) | `agents_controller.dart:152` (`testRunAgent`/`getRunDetail` public API — chưa xác nhận có UI thật gọi tới) | Ngoài phạm vi được sửa lần này để giữ blast radius nhỏ; response backend là `WorkforceRunDetailOut` (có `input_payload`/`output_payload`), chưa có model Dart tương ứng trong `workforce_mvp_models.dart`. Cần một lát cắt riêng. |
| `AgentPlatformService.listAgents` / `getAgents` / `AgentsService.getAgents` | `GET /workforce/agents` (+ `AgentsService` có thêm fallback `GET /agents/?workspace_id=`, cũng không tồn tại) | `GET /agent/workforce/roster` (`apps/cosa/api/workforce_routes.py::get_roster`) | **canonical (đã đóng 2026-09-04)** | `hub_control_plane_mixin.dart:92` (Founder Dashboard, hiển thị roster); `agents_controller.dart:57` (`AgentsView`) | Nguồn dữ liệu = `FUNCTIONAL_AGENT_CATALOG` (6 entry thật) + trạng thái assignment thật theo workspace — KHÔNG phải 12 agent hư cấu `default12Agents` từng fallback khi lỗi (đã xoá hẳn constant đó). Cả 2 class (`AgentPlatformService`, `AgentsService`) đều migrate sang `WorkforceMvpService.listRoster()`. |
| `AgentsService.getRuntimes` | `GET /workforce/runtimes` | Không tìm thấy | `unknown` | `agents_controller.dart:90` | Read-only, không phải mutation — không chặn release nhưng cần theo dõi. Ngoài phạm vi đợt đóng 2026-09-04. |
| `AgentPlatformService.getDashboardSummary` | `GET /workforce/dashboard-summary` | `GET /agent/workforce/dashboard-summary` (`apps/cosa/api/workforce_routes.py::get_dashboard_summary`) | **canonical (đã đóng 2026-09-04)** | `hub_control_plane_mixin.dart:83` (Founder Dashboard, tóm tắt số liệu) | Aggregator in-process thuần (roster/work-products/exceptions/approvals đã có sẵn) — không route mới nào tự thân, không migration DB. |
| `AgentsService.getDashboardSummary` | `GET /workforce/dashboard-summary` | Không tìm thấy | **unknown — BLOCKS RELEASE (chưa đóng)** | `agents_controller.dart:45` (`loadDashboardSummary`) | **Method riêng biệt** với `AgentPlatformService.getDashboardSummary` ở trên — KHÔNG nằm trong phạm vi đợt migrate 2026-09-04, vẫn gọi thẳng route chết qua `ApiClient.get` thô. Phát hiện khi rà `AgentsService` cho dòng phía trên; ghi nhận riêng để không lẫn với dòng đã đóng. |
| `AgentPlatformService.listWorkProducts` | `GET /workforce/work-products` | `GET /agent/workforce/artifacts` (`apps/cosa/api/workforce_routes.py::list_work_products`) | **canonical (đã đóng 2026-09-04)** | `hub_control_plane_mixin.dart:110`, `work_product_viewer_dialog.dart` | MVP: "work product" = artifact workspace-wide có sẵn, không phải workflow DRAFT/REVIEW riêng. `content_markdown` chưa fetch được (known gap, xem spec Phase 2) — FE cần fallback hiển thị link `object_ref`. |
| `AgentPlatformService.acceptWorkProduct` / `requestWorkProductRevision` | `POST /workforce/work-products/{id}/accept` / `.../revise` | Không tìm thấy | **unknown — BLOCKS RELEASE (mutation, chưa đóng)** | `work_product_viewer_dialog.dart` | Mutation người dùng chạm tới, ngoài phạm vi đợt 2026-09-04 (chỉ đóng phần list read-only). Chưa xác nhận domain accept/revise thật. |
| `AgentPlatformService.getStageRoster` | `GET /workforce/stage-roster` | `GET /agent/workforce/stage-roster/{stage_code}` (`apps/cosa/api/workforce_routes.py::get_stage_roster`, proxy sang `services/company` `GET /operations/tasks/stage-roster/:stageCode`) | **canonical (đã đóng 2026-09-04)** | `hub_control_plane_mixin.dart:124` | ⚠️ `stage_code` chỉ có 2 giá trị thật trả roster non-empty hôm nay — `P0_DISCOVERY`/`P1_PROBLEM_VALIDATION` (CHECK constraint `strategy.project_operating_setups.selected_stage`, migration `34_project_operating_setups.up.sql`) — không phải dải P0-P6 UI từng ghi. Mã khác không lỗi, chỉ trả roster rỗng. |
| `AgentPlatformService.checkAgentStageFit` | `GET /workforce/stage-fit` | Không tìm thấy | `unknown` | `hub_control_plane_mixin.dart:124` lân cận | Read path, ngoài phạm vi đợt 2026-09-04 — theo dõi, không tự phân loại `intentionally-unsupported`. |
| `AgentPlatformService.listEscalations` | `GET /workforce/exceptions` | `GET /agent/workforce/exceptions` (`apps/cosa/api/workforce_routes.py::list_exceptions`, **read-only**) | **canonical (đã đóng 2026-09-04, phạm vi thu hẹp có chủ đích)** | `hub_control_plane_mixin.dart:147` | MVP: "escalation" = run `FAILED` trong workspace (không phải domain exception/tier thật). `tier` LUÔN hằng số `"LEAD_NOTIFY"` — không tự gán `FOUNDER_GATE`. |
| `AgentPlatformService.resolveEscalation` | `POST /workforce/exceptions/{id}/resolve` | **Không tồn tại theo chủ đích** — loại khỏi phạm vi | **intentionally-unsupported (quyết định kiến trúc 2026-09-04)** | Không còn caller nào (method đã xoá khỏi `AgentPlatformService` sau final review) | `force_approve`/`increase_budget`/`block_permanently` là hành động rủi ro cao theo CLAUDE.md quy tắc 8 — cần một phiên thiết kế domain escalation riêng (tier/action) trước khi xây backend, xem spec `2026-09-04-workforce-dashboard-backend-gaps-design.md` Phase 5 "ngoài phạm vi". Nút Resolve trên UI đã bị vô hiệu hoá từ 2026-09-02 (trước cả plan này). |
| `AgentPlatformService.reportStageMismatch` / `runExceptionWatchdog` | `POST /workforce/exceptions/stage-mismatch`, `.../watchdog` | Không tìm thấy | `unknown` | `hub_control_plane_mixin.dart:175,306` | Ngoài phạm vi đợt 2026-09-04 — theo dõi. |
| `AgentPlatformService.listDecisions` / `acceptDecision` | `GET/POST /workforce/decisions...` | Không tìm thấy | **unknown — BLOCKS RELEASE** | `decision_records_dialog.dart` | Mutation (`acceptDecision`) không có backend xác nhận. |
| `AgentPlatformService.listHeartbeats` / `checkStalledRuns` / `listRoutines` / `triggerRoutine` | `GET/POST /workforce/heartbeats...`, `/routines...` | Không tìm thấy | `unknown` | `agent_routines_dialog.dart` | `triggerRoutine` là mutation — cần xác nhận trước khi release. |
| `AgentPlatformService.getBudgets` / `setBudget` / `getCostLedger` | `GET/POST /workforce/budgets`, `/cost-ledger` | Không tìm thấy | `unknown` | Không tìm thấy consumer sống nào gọi các method này (đã grep toàn repo `frontend/lib`) | Có thể là dead code chưa dọn — nhưng vì không chắc chắn 100% (dialog có thể chưa được `grep` bắt được do dynamic dispatch), giữ `unknown` thay vì tự tin xoá. |
| `AgentPlatformService.createOrUpdateAgent` / `cloneAgent` / `updateAgentTools` / `listTools` / `createWebhookTool` / `listSkills` / `uploadSkillMarkdown` / `testRouting` / `getTools` | `GET/POST /workforce/agents`, `/tools...`, `/skills/physical`, `/routing/test`, `POST /skills/upload-markdown` | Không tìm thấy (ngoại trừ `/skills/upload-markdown` được `ApiClient.normalizeEndpoint` map sang `/agent/skills/upload-markdown` — nhưng `skill_registry_routes.py` cần xác nhận có endpoint này) | `unknown` | Đã có test cũ (`test/agent_platform_service_test.dart`) khoá hành vi 404-hiện-tại của `getAgents`/`getTools`/`testRouting` — không đổi trong commit này. | Ngoài phạm vi Task 7 (không có UI Dashboard sống nào được xác nhận gọi các method quản trị agent/tool/skill này ngoài test cũ) — không tự chế thay thế. |
| `AgentsService.createAgent` / `updateAgent` / `deleteAgent` / `resetSystemPrompt` / `listPromptRevisions` | `POST /workforce/agents`, `PATCH/DELETE /agents/{id}...` | Không tìm thấy | `unknown` | Không xác nhận UI gọi (chỉ có test cũ khoá hành vi) | Giữ nguyên, ngoài phạm vi. |

## Marketing domain

Không có thay đổi. Đã rà `frontend/lib/modules/marketing/services/marketing_service.dart`
qua route inventory (`rg -n "✗ GHOST" ... | rg marketing`) — toàn bộ route
`/marketing/*` đều GHOST (không có router `/agent/marketing` hay tương đương
nào tồn tại trong `apps/cosa/api`), nhưng **không có bằng chứng nào về route
canonical thay thế** để migrate sang. Theo brief Task 7 ("Repeat for Marketing
only after its backend contract is verified... Do not map arbitrary
`/marketing/*` trong `ApiClient.normalizeEndpoint` as a shortcut"), không sửa
`marketing_service.dart` trong commit này.

## Tóm tắt quyết định release

- **Fixed trong Task 7 (2026-09-02)**: approvals (list/approve/reject),
  org-chart, runs list — 3 route nhóm, có route backend thật xác nhận
  mounted, có consumer sống trên Founder Dashboard.
- **Fixed trong plan workforce-dashboard-backend-gaps + follow-up
  (2026-09-04)**: agents roster list (`AgentPlatformService`/`AgentsService`
  cùng migrate), dashboard-summary (chỉ `AgentPlatformService`), work
  products list (read-only), stage roster get (read-only), escalations list
  (read-only) — 5 route mới ở `apps/cosa/api/workforce_routes.py`, không
  route mutation nào (`resolveEscalation`, `acceptWorkProduct`,
  `requestWorkProductRevision`) được xây trong đợt này — vẫn `unknown` hoặc
  `intentionally-unsupported`, xem bảng phía trên.
- **Vẫn `unknown`, chưa đóng, ngoài phạm vi 2 đợt trên**:
  `AgentsService.getDashboardSummary` (method riêng biệt, dễ nhầm với dòng
  đã đóng), `getRuntimes`, `checkAgentStageFit`, `acceptWorkProduct`/
  `requestWorkProductRevision`, `reportStageMismatch`/`runExceptionWatchdog`,
  decisions, heartbeats/routines, budgets/cost-ledger, agent/tool/skill CRUD
  — không có route backend nào khớp sau khi grep toàn bộ
  `apps/cosa/api/*.py`. Trước khi đóng thêm dòng nào, xác nhận có consumer
  UI sống thật (nhiều dòng trong nhóm này chưa xác nhận được, xem ghi chú
  gốc từng dòng).
- **`intentionally-unsupported` theo quyết định kiến trúc (không phải
  gap)**: `resolveEscalation` — cần thiết kế domain escalation riêng (tier/
  action rủi ro tài chính/quyền) trước khi xây, xem
  `docs/superpowers/specs/2026-09-04-workforce-dashboard-backend-gaps-design.md`.
