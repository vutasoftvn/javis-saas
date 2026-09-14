# Hub Workforce/Approval Project Scope — Design

Status: DRAFT (chờ user review)
Ngày: 2026-09-14
Phạm vi: sub-project #4/6 trong đợt audit "Ba blocker lớn nhất" (2026-09-14) — P1.
Các sub-project khác có spec riêng:
[#1 Schedule Project scope](2026-09-14-schedule-project-scope-design.md),
[#2 Python quality gates](2026-09-14-python-quality-gates-design.md),
[#3 Semantic Knowledge production wiring](2026-09-14-semantic-knowledge-production-wiring-design.md).

## Vấn đề

Audit ban đầu nêu: `WorkforceMvpService` trả `unavailable` cố định, nhưng
Founder Hub vẫn tải approvals/packs khi khởi tạo. UI có phản ánh
`unavailable`, nhưng capability thực tế không thể hoạt động. Đề xuất: hoặc
khôi phục route Project-aware có authority/contract đầy đủ, hoặc bỏ panel
khỏi Hub.

**Xác nhận lại và mở rộng phạm vi trong quá trình điều tra (2026-09-14):**

- `WorkforceMvpService` (`frontend/lib/modules/workforce/services/
  workforce_mvp_service.dart`) — toàn bộ 11 method trả
  `MvpRequestClient.unavailable(...)`, comment nói rõ "Founder Trial R1 —
  legacy surface removed from the MVP contract".
- **Phạm vi gọi thực tế rộng hơn audit nêu:** không chỉ
  `founder_command_center_controller.dart` (gọi `listApprovals`,
  `getComposition` qua `listWorkforcePacks`), mà `hub_control_plane_mixin.
  dart` và `mission_control_controller.dart` cũng gọi `listRuns`,
  `decideApproval`, `getDashboardSummary`, `listWorkProducts`,
  `getStageRoster` — tất cả qua cùng service bị stub (`AgentPlatformService`
  cũng chỉ là wrapper mỏng của `WorkforceMvpService`).
- **Phát hiện quan trọng: backend KHÔNG hề stub** — cả 7 route liên quan
  (`GET /assignments`, `/composition`, `/roster`, `/artifacts`,
  `/stage-roster/{code}`, `/dashboard-summary`, `/runs`, `/approvals`,
  `POST /approvals/{id}/decision`) là route **thật, đang hoạt động** trong
  `apps/cosa/api/workforce_routes.py` (1105 dòng). Vấn đề chỉ có 2 lớp:
  (a) tất cả các route này hiện **chỉ scope theo `workspace_id`, không có
  `project_id`**; (b) Flutter tự stub cứng client bất kể backend đã sẵn
  sàng.
- **Xác nhận `agent.workforce_assignments` không vi phạm "một danh tính
  workforce duy nhất":** migration `packages/agent/migrations/
  003_add_workforce_member_reference.sql` cho thấy bảng này có cột
  `company_workforce_member_id` tham chiếu đúng `WorkforceMember` canonical
  — đây là bảng "assignment" (kích hoạt agent domain cho workspace), không
  phải bảng nhân sự riêng.
- `packages/agent/capabilities/approval_service.py` — `DurableApprovalService`
  thật, `RunApprovalRecord` (`packages/agent/runs/models.py:201-221`) đã có
  sẵn `project_id` ở **write path** (`create_change_approval_request`,
  dòng 156-177). Chỉ **read path** (`list_pending_approvals`, dòng 296-302)
  chưa nhận `project_id` — nghĩa là dữ liệu đã đủ, chỉ thiếu filter khi đọc.
- **Bug UX thật phát hiện thêm (chưa từng có trong audit gốc):**
  `hologram_hub_view.dart` (dòng 480) truyền `controller.pendingApprovals`
  (danh sách luôn rỗng vì gọi `listApprovals()` luôn fail) cho
  `WaitingForYouWidget`, nhưng **không hề đọc** `approvalsState` (đã được
  set `unavailable` ở `founder_command_center_controller.dart:651` nhưng bị
  bỏ qua bởi view). Kết quả: founder thấy "0 approval đang chờ" — trông như
  không có gì cần làm — trong khi thực tế toàn bộ subsystem approval đang
  unavailable. Đây là kiểu "bịa dữ liệu 'không có gì'" cùng họ với vấn đề
  audit item #5 (Flutter DTO fallback dữ liệu tài chính), chỉ khác domain.

## Quyết định đã chốt

Khôi phục route Project-aware có authority/contract đầy đủ cho **toàn bộ 7
route đang thực sự được gọi** (không chỉ 2 route audit nêu ban đầu):
`listApprovals`, `decideApproval`, `getComposition`/`listRoster`
(`/composition`, `/roster` dùng chung repo), `getStageRoster`,
`getDashboardSummary`, `listRuns`. `listWorkProducts` (`/artifacts`) **để
lại** — xem phần Ngoài phạm vi.

## Kiến trúc

```
Backend (apps/cosa/api/workforce_routes.py) — áp dụng đồng loạt:
  + project_id: str = Query(...) bắt buộc
  + verify_project_context(plane, identity, project_id) trước khi query
    (pattern đã có ở conversation_routes.py)
  + repo/service query filter theo (workspace_id, project_id)

agent.workforce_assignments (migration Expand):
  + project_id (nullable schema, bắt buộc tầng ứng dụng cho insert mới)
    + is_legacy_unscoped — TÁI DÙNG chính sách backfill đã chốt ở spec #1
      (auto-gán project đầu tiên, đánh dấu legacy), không phát minh chính
      sách mới.

ApprovalService.list_pending_approvals: thêm param project_id (write path
  RunApprovalRecord đã có sẵn — chỉ thiếu ở read path).

Flutter (WorkforceMvpService): bỏ unavailable() cho đúng 7 method, gọi
  route thật với project_id = activeProjectId. Chưa có Project đang hoạt
  động -> KHÔNG gọi, hiển thị trạng thái "chọn Project".
```

**Cần xác nhận trong lúc viết plan (không tự quyết ở đây):**
- `/artifacts` (work products): docstring hiện tại nói rõ "workspace-wide"
  là quyết định MVP có chủ đích (tham chiếu
  `docs/superpowers/specs/2026-09-04-workforce-dashboard-backend-gaps-design.md`
  Phase 2) — đọc lại spec đó trước khi đổi sang Project-scope.
- `GET /stage-roster/{code}` proxy sang `services/company`
  (`GET /operations/tasks/stage-roster/:stageCode`) — cần xác nhận endpoint
  company có nhận `project_id` hay chỉ toàn workspace; nếu company-side
  chưa hỗ trợ, đây là dependency liên-plane cần làm trước ở `services/
  company`, không phải chỉ ở `apps/cosa`.

## Data model & Flutter wiring

**Migration** `agent.workforce_assignments` (nối tiếp trong
`packages/agent/migrations/`):
- Thêm `project_id TEXT` (nullable schema) + `is_legacy_unscoped BOOLEAN
  NOT NULL DEFAULT false`.
- Backfill: assignment cũ → `project_id` = project đầu tiên của workspace,
  `is_legacy_unscoped = true`. Workspace không còn project → assignment
  chuyển `status = 'RETIRED'`, không để `project_id NULL` trôi nổi.

**7 route:**

| Route | Thay đổi |
|---|---|
| `GET /assignments`, `/composition`, `/roster` | `project_id` Query bắt buộc; `repo.list_assignments(workspace_id, project_id, status=...)` |
| `GET /artifacts` | Giữ nguyên workspace-wide cho tới khi xác nhận spec 2026-09-04 |
| `GET /stage-roster/{code}` | `project_id` Query bắt buộc, forward vào proxy company — dependency liên-plane cần xác nhận |
| `GET /dashboard-summary` | Tự động Project-scoped khi 3 nguồn nó gộp (`/roster`, `/approvals`) đã nhận `project_id`; `/artifacts` giữ nguyên |
| `GET /runs` | `project_id` Query bắt buộc, `plane.repository.list_runs(workspace_id, project_id, limit)` |
| `GET /approvals` | `project_id` Query bắt buộc → `ApprovalService.list_pending_approvals(workspace_id, project_id)` |
| `POST /approvals/{id}/decision` | Defense-in-depth: verify `RunApprovalRecord.project_id` khớp `project_id` caller gửi, cùng nguyên tắc "không tin payload" ở `handlers.py:190-226` |

**Flutter:**

- `workforce_mvp_service.dart`: bỏ `unavailable()` cho 7 method
  (`listApprovals`, `decideApproval`, `getComposition`, `listRoster`,
  `getStageRoster`, `getDashboardSummary`, `listRuns`), mỗi method thêm
  `required String projectId`.
- Giữ nguyên `unavailable()` cho `listRunEvents`, `listExceptions`,
  `getOrgChart`, `listWorkProducts` — không mở rộng ngoài phạm vi đã xác
  nhận có route thật + được yêu cầu khôi phục.
- `hologram_hub_controller.dart`/`hub_control_plane_mixin.dart`/
  `mission_control_controller.dart`: thêm guard `if (activeProjectId ==
  null) return;` trước mọi callsite, tái dùng pattern đã có ở
  `founder_command_center_controller.dart:600`.
- **Sửa bug UX đã phát hiện:** `WaitingForYouWidget` nhận thêm
  `approvalsState` để phân biệt "0 approval (loaded, rỗng thật)" với
  "unavailable (lỗi tải)" — không còn gộp chung 1 giao diện.

## Testing

**Backend** (`make apps-cosa-test`):

1. 6 route đổi (`/assignments`, `/composition`, `/roster`, `/runs`,
   `/approvals`, `/approvals/{id}/decision`): thiếu `project_id` → 422;
   `project_id` không thuộc workspace → 404.
2. `list_assignments`/`get_composition`/`get_roster`: seed 2 Project cùng
   workspace, mỗi Project có assignment khác nhau → route chỉ trả đúng
   Project được truyền.
3. `list_pending_approvals`: seed approval ở Project A và B → gọi
   `project_id=A` chỉ trả approval của A.
4. `decide_approval`: mismatch — approval thuộc A, request gửi
   `project_id=B` → reject, không cho quyết định.
5. Migration backfill: workspace không còn project → assignment
   `RETIRED`, không để `project_id NULL`.

**Frontend** (`make frontend-test`):

6. `WorkforceMvpService`: 7 method gọi `MvpRequestClient` thật với
   `project_id` trong query — mock HTTP, assert URL/params đúng.
7. `WaitingForYouWidget`: 2 trạng thái `unavailable` vs `loaded` + rỗng
   phải hiển thị UI khác nhau rõ ràng.
8. Guard `activeProjectId == null` → không gọi API, hiển thị "chưa chọn
   Project".

**E2E** (`make e2e-cross-plane-smoke`): tái dùng thiết lập "2 Project
trong 1 workspace" từ spec #1 — thêm assertion Hub mở Project A không hiển
thị approval/roster của Project B.

## Ngoài phạm vi (out of scope)

- `listWorkProducts`/`/artifacts` Project-scope — chờ xác nhận spec
  2026-09-04 có chủ đích giữ workspace-wide hay không.
- `listRunEvents`, `listExceptions`, `getOrgChart` — không có bằng chứng
  đang được gọi từ Hub/Mission Control hiện tại; giữ `unavailable()`.
- Thay đổi endpoint `services/company` cho `stage-roster` nhận `project_id`
  — nếu cần, là 1 thay đổi riêng ở `services/company`, ghi nhận dependency,
  không tự ý mở rộng phạm vi TS trong spec này.
