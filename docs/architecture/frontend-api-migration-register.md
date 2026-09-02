# Frontend API Migration Register

Nguồn: `docs/architecture/generated/route-inventory.md` (sinh bởi
`python scripts/route_inventory.py`) tại thời điểm 2026-09-02, đối chiếu trực
tiếp với các router thật sự được `include_router()` trong
`apps/cosa/api/app.py` (không suy diễn từ tên file router).

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
| `AgentPlatformService.listAgents` / `getAgents` / `AgentsService.getAgents` | `GET /workforce/agents` | **Không tìm thấy** — không có router `/agent/workforce/agents` hay bất kỳ router nào khác định nghĩa GET agents list | **unknown — BLOCKS RELEASE** | `hub_control_plane_mixin.dart:92` (Founder Dashboard, hiển thị roster) | Đã grep toàn bộ `apps/cosa/api/*.py`: không có route nào khớp. Có thể `/agent/workforce/composition` hoặc `/agent/workforce/assignments` là ý định thay thế (cùng khái niệm FUNCTIONAL_AGENT_CATALOG) nhưng field shape khác hẳn (`WorkforceCompositionEntry` không có `name`/`department`/`status` như UI đang dùng) — **không tự suy diễn thay thế, cần chủ sở hữu domain xác nhận**. |
| `AgentsService.getRuntimes` | `GET /workforce/runtimes` | Không tìm thấy | `unknown` | `agents_controller.dart:90` | Read-only, không phải mutation — không chặn release nhưng cần theo dõi. |
| `AgentPlatformService.getDashboardSummary` / `AgentsService.getDashboardSummary` | `GET /workforce/dashboard-summary` | Không tìm thấy | **unknown — BLOCKS RELEASE** | `hub_control_plane_mixin.dart:83` (Founder Dashboard, tóm tắt số liệu) | Không có route nào khớp trong toàn bộ `apps/cosa/api`. |
| `AgentPlatformService.listWorkProducts` / `acceptWorkProduct` / `requestWorkProductRevision` | `GET/POST /workforce/work-products...` | Không tìm thấy | **unknown — BLOCKS RELEASE** (mutation người dùng chạm tới) | `hub_control_plane_mixin.dart:110,222`, `work_product_viewer_dialog.dart` | Backend không có khái niệm "work product" ở bất kỳ router nào đã mount. |
| `AgentPlatformService.getStageRoster` / `checkAgentStageFit` | `GET /workforce/stage-roster`, `.../stage-fit` | Không tìm thấy | `unknown` | `hub_control_plane_mixin.dart:124` | Read path, không phải mutation trực tiếp — theo dõi, không tự phân loại `intentionally-unsupported`. |
| `AgentPlatformService.listEscalations` / `resolveEscalation` / `reportStageMismatch` / `runExceptionWatchdog` | `GET/POST /workforce/exceptions...` | Không tìm thấy | **unknown — BLOCKS RELEASE** (resolveEscalation là mutation rủi ro: retry/reassign/force_approve/increase_budget/block_permanently) | `hub_control_plane_mixin.dart:147,175,306` | Đặc biệt đáng chú ý: `force_approve`/`increase_budget` là hành động rủi ro cao theo CLAUDE.md quy tắc 8 — nếu route này thật sự chưa tồn tại ở backend, UI đang cho phép người dùng bấm một hành động không bao giờ thành công (hoặc tệ hơn, âm thầm không làm gì). Cần chủ sở hữu domain xác nhận khẩn. |
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

- **Fixed trong Task 7**: approvals (list/approve/reject), org-chart, runs
  list — 3 route nhóm, có route backend thật xác nhận mounted, có consumer
  sống trên Founder Dashboard.
- **Blocks release nếu ai đó coi các dialog/mixin liên quan là "hoạt động
  đầy đủ"**: dashboard-summary, agents roster list, work-products,
  escalations (đặc biệt `resolveEscalation` với action tài chính/quyền), 
  decisions, heartbeats/routines — tất cả `unknown`, không có route backend
  nào khớp sau khi grep toàn bộ `apps/cosa/api/*.py`.
