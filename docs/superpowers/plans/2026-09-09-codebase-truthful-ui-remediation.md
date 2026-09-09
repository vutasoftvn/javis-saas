# Codebase Truthful UI Remediation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (- [ ]) syntax for tracking.

**Goal:** Khôi phục release gates và biến COSA Hub cùng dashboard thành giao diện quản trị thống nhất, đúng quyền, không trình bày dữ liệu lỗi như dữ liệu nghiệp vụ thật.

**Architecture:** Business truth vẫn ở services; Agent Platform chỉ điều phối qua capability và governance; Flutter chỉ hiển thị structured state. Hub là bề mặt Hôm nay của Founder; module nghiệp vụ giữ route canonical /work/*, chung policy visibility và locale.

**Tech Stack:** Flutter/GetX, Encore TypeScript, FastAPI/Python, PostgreSQL, MvpRequestClient, Flutter widget/golden tests, Vitest, pytest.

**Spec:** docs/superpowers/specs/2026-09-04-command-center-dashboard-redesign-design.md; docs/architecture/CODEBASE_HARDENING_2026-09-08.md; docs/superpowers/specs/2026-09-06-release-gate-recovery-design.md.

## Global Constraints

- Làm trực tiếp trên main; không tạo worktree, không sửa thay đổi sẵn có ngoài phạm vi.
- Authorization và tenant isolation ở service/handler; guard Flutter chỉ là UX.
- Không dùng allowlist để che route frontend thiếu contract.
- Không dùng số 0, danh sách rỗng hoặc tick xanh thay cho loading, unavailable hay stale.
- Secret upload/JWT/delegation token không nằm query URL hoặc log.
- Finance/legal chỉ lấy rule từ regime pack versioned đã được phê duyệt.
- Mỗi thay đổi hành vi phải red → green test rồi chạy gate liên quan.

## Decision Gates

1. Product Owner duyệt IA: Hôm nay, Công việc, Chiến lược, Đội ngũ AI, Thêm; Finance/Legal/CRM chỉ hiện khi capability hợp lệ.
2. Legal/accounting owner xác nhận jurisdiction, văn bản còn hiệu lực, entity scope, kỳ báo cáo và version regime pack trước hạng mục Finance.
3. Hạng mục ghi IMPLEMENTED/WIRED/VERIFIED trong evidence 2026-09-08 chỉ tái xác minh trước; chỉ sửa khi tái hiện regression.

## File Map

| Vùng | File | Vai trò |
|---|---|---|
| Build/locale | frontend/lib/core/localization/app_translations.dart; ba file Strategy | Compile sạch và runtime locale hoàn chỉnh. |
| Hub state | founder_command_center_controller.dart; hologram_hub_view.dart; Hub widgets | Loading/error/empty/data tường minh. |
| Visibility | module_visibility_controller.dart; dashboard_nav_config.dart | Menu, sidebar, route guard cùng policy. |
| Contract | shared/contracts/mvp-surface.json; auth_service.dart | Một route có một contract. |
| Vault | apps/cosa/api/vault_routes.py; Flutter Vault service/model | Upload token header, streaming. |
| Finance/legal | accounting regime/report/legal applicability services | Resolve rule theo pack/version được duyệt. |

---

### Task 1: Khôi phục Flutter compile và locale Tasks

**Files:**
- Modify: frontend/lib/modules/strategy/services/strategy_service_base.dart
- Modify: frontend/lib/modules/strategy/widgets/twelve_wy/twelve_wy_empty_state.dart
- Modify: frontend/lib/modules/strategy/widgets/funding/funding_watchlist_tab_content.dart
- Modify: frontend/lib/core/localization/app_translations.dart
- Create: frontend/test/core/localization/app_translations_tasks_test.dart

**Interfaces:**
- Produces: AppTranslations.vi và AppTranslations.en chứa toàn bộ viTasks/enTasks.
- Produces: mọi caller .tr import package:get/get.dart.

- [ ] **Step 1: Viết test đỏ.**

  Tạo test sau:

```dart
expect(AppTranslations.vi[L10nKey.tasksStatusTodo], 'Cần làm');
expect(AppTranslations.en[L10nKey.tasksStatusTodo], 'To Do');
expect(AppTranslations.vi[L10nKey.tasksDialogSave], isNotNull);
expect(AppTranslations.en[L10nKey.tasksDialogSave], isNotNull);
```

- [ ] **Step 2: Chạy để xác nhận lỗi.**

  Run: cd frontend && flutter test test/core/localization/app_translations_tasks_test.dart

  Expected: fail compile vì String.tr không có extension, hoặc test fail vì maps không spread task locale.

- [ ] **Step 3: Sửa tối thiểu.**

  Thêm import GetX vào đúng ba file gọi .tr. Thêm ...viTasks vào map vi và ...enTasks vào map en. Không đổi identifier hoặc nội dung dịch.

- [ ] **Step 4: Xác minh.**

  Run: cd frontend && flutter test test/core/localization/app_translations_tasks_test.dart && flutter analyze

  Expected: pass, analyzer không còn errors/warnings từ các file trên.

- [ ] **Step 5: Commit.**

  Commit: fix(frontend): restore localization build baseline

### Task 2: Khép contract profile locale và workspace auth

**Files:**
- Modify: shared/contracts/mvp-surface.json
- Modify: frontend/lib/modules/auth/services/auth_service.dart
- Modify: handler/service Control Plane đang phục vụ PATCH /platform/auth/me, nếu endpoint đó còn canonical
- Modify: tests/quality/test_frontend_api_contracts.py
- Modify/Create: services/cosa/tests/*profile* và frontend/test/modules/auth/* test phù hợp

**Interfaces:**
- Consumes: Authorization caller và workspace đã chọn.
- Produces: profile locale chỉ của caller; không nhận target userId/workspaceId từ client.

- [ ] **Step 1: Viết tests negative.**

  Flutter test fake API client và assert update locale đi qua endpoint contract. Encore test assert caller A không PATCH locale của B và invalid locale bị 4xx.

- [ ] **Step 2: Chạy gate đỏ.**

  Run: make frontend-api-contract-check

  Expected: fail chỉ ra /platform/auth/me không nằm canonical contract, hoặc test route mới fail.

- [ ] **Step 3: Reconcile route thay vì thêm allowlist.**

  Nếu PATCH /platform/auth/me là đường chạy thật có server authorization, manifest hoá chính xác method/path/schema/frontend symbol/backend test và thay literal frontend bằng endpoint named. Nếu không, xoá lời gọi và dùng endpoint profile canonical đã có.

```ts
type UpdateMyProfileRequest = {
  preferred_locale?: "vi-VN" | "en-US";
};
// Caller được suy ra từ Authorization.
```

- [ ] **Step 4: Xác minh authority.**

  Run: make frontend-api-contract-check && make route-auth-allowlist-check && cd services/cosa && encore test

  Expected: contract xanh; anonymous, foreign-workspace và invalid locale bị từ chối.

- [ ] **Step 5: Commit.**

  Commit: fix(contract): reconcile profile locale endpoint

### Task 3: Làm Hub trung thực với dữ liệu

**Files:**
- Modify: frontend/lib/modules/hologram_hub/controllers/founder_command_center_controller.dart
- Modify: frontend/lib/modules/hologram_hub/views/hologram_hub_view.dart
- Modify: frontend/lib/modules/hologram_hub/widgets/pulse_stat_bar_widget.dart
- Modify: frontend/lib/modules/hologram_hub/widgets/waiting_for_you_widget.dart
- Modify: frontend/lib/modules/hologram_hub/widgets/ai_workforce_tab.dart
- Create: frontend/test/modules/hologram_hub/widgets/waiting_for_you_widget_test.dart
- Modify: frontend/test/modules/hologram_hub/ai_workforce_tab_test.dart
- Modify: frontend/test/modules/hologram_hub/founder_command_center_approvals_test.dart
- Modify: frontend/test/modules/hologram_hub/widgets/pulse_stat_bar_widget_test.dart

**Interfaces:**

```dart
enum HubLoadState { idle, loading, loaded, unavailable }

final Rx<HubLoadState> pulseState;
final Rx<HubLoadState> approvalsState;
final Rx<HubLoadState> workforceState;
```

- [ ] **Step 1: Viết tests đỏ cho bốn trường hợp.**

  - Pulse null/unavailable hiển thị error/retry, không có 0/0.
  - approvals failure và decisions rỗng không hiển thị tick xanh.
  - approvals failure và có decision hiển thị decision cộng error của approvals.
  - workforce failure khi render HologramHubView hiển thị unavailable card.

- [ ] **Step 2: Chạy tests để thấy failure hiện tại.**

  Run: cd frontend && flutter test test/modules/hologram_hub/widgets/pulse_stat_bar_widget_test.dart test/modules/hologram_hub/ai_workforce_tab_test.dart test/modules/hologram_hub/founder_command_center_approvals_test.dart

  Expected: default zero, queue xanh, hoặc Workforce state không đi tới view.

- [ ] **Step 3: Cài đặt state rõ ràng.**

  Trong loadDashboardData: loading trước request; loaded khi response hợp lệ; unavailable khi failure/exception; chỉ replace list khi success; reset workspace về idle. AiWorkforceTab bắt buộc nhận state:

```dart
AiWorkforceTab(
  packs: controller.workforcePacks.toList(),
  loadState: controller.workforceState.value,
  onTogglePack: controller.togglePack,
);
```

  WaitingForYouWidget chỉ empty-success khi approvals loaded và hai danh sách rỗng. Pulse dùng skeleton khi loading, error surface có retry khi unavailable, và stats chỉ ở loaded.

- [ ] **Step 4: Kiểm thử responsive/accessibility.**

  Chạy widget tests tại 1440, 1024, 768, 390. Error có icon, label và retry semantic; không đổi business authority approve/reject.

- [ ] **Step 5: Gate và commit.**

  Run: cd frontend && flutter test test/modules/hologram_hub && flutter analyze

  Commit: fix(hub): expose loading and unavailable states

### Task 4: Đồng bộ menu module, sidebar và route guard

**Files:**
- Modify: frontend/lib/modules/hologram_hub/views/hologram_hub_view.dart
- Modify: frontend/lib/modules/dashboard/views/widgets/dashboard_sidebar.dart
- Modify: frontend/lib/modules/dashboard/models/dashboard_nav_config.dart
- Modify: frontend/test/modules/hologram_hub/hologram_hub_view_module_switcher_test.dart
- Modify: frontend/test/core/routing/module_visibility_redirect_test.dart
- Modify: frontend/test/modules/dashboard/dashboard_sidebar_test.dart

**Interfaces:**
- Consumes: ModuleVisibilityController.isVisible(WorkspaceModule).
- Produces: modal Hub, sidebar và deep-link guard dùng cùng predicate.

- [ ] **Step 1: Viết tests đỏ.**

  Seed visibility với Finance, Legal, Sales hidden. Mở switcher và assert ba labels không tồn tại, core module vẫn tồn tại; deep-link /work/finance vẫn redirect /hub.

- [ ] **Step 2: Chạy tests.**

  Run: cd frontend && flutter test test/modules/hologram_hub/hologram_hub_view_module_switcher_test.dart test/core/routing/module_visibility_redirect_test.dart

  Expected: Hub switcher đang liệt kê item không visible.

- [ ] **Step 3: Implement predicate chung.**

  Bọc modal bằng Obx; sau moduleForLegacyIndex lọc visibilityController.isVisible(module). Khi snapshot chưa tải chỉ render core module và loading surface cho optional modules. Giữ ModuleVisibilityGuardMiddleware làm enforcement độc lập.

- [ ] **Step 4: Thêm UX redirect có nghĩa.**

  Redirect chỉ hiện một message local: “Module này chưa được bật cho workspace hoặc tài khoản của bạn.” Không lộ role/capability chi tiết; không loop; không hiện khi user mở Hub chủ động.

- [ ] **Step 5: Gate và commit.**

  Run: cd frontend && flutter test test/core/services/module_visibility_controller_test.dart test/core/routing/module_visibility_redirect_test.dart test/modules/dashboard/dashboard_sidebar_test.dart test/modules/hologram_hub/hologram_hub_view_module_switcher_test.dart && flutter analyze

  Commit: fix(frontend): align module visibility with navigation

### Task 5: Tái cấu trúc Hub và dashboard theo IA duyệt

**Files:**
- Modify: frontend/lib/modules/hologram_hub/views/hologram_hub_view.dart
- Modify: frontend/lib/modules/dashboard/models/dashboard_nav_config.dart
- Modify: frontend/lib/core/shell/app_shell.dart
- Modify: frontend/lib/core/theme/app_theme.dart
- Create: frontend/lib/modules/hologram_hub/widgets/hub_section_header.dart
- Create: frontend/lib/modules/hologram_hub/widgets/hub_status_surface.dart
- Create: frontend/test/modules/hologram_hub/hub_responsive_golden_test.dart
- Modify: frontend/test/core/shell/app_shell_test.dart

**Interfaces:**
- Hub: Hôm nay và Đội ngũ AI. Hôm nay chứa context, queue, top priorities, pulse, chat.
- Module nav: Công việc, Chiến lược, Đội ngũ AI, Thêm; visible list vẫn từ DashboardNavConfig.
- HubStatusSurface consumes title, detail, HubLoadState và retry callback.

- [ ] **Step 1: Ghi approved IA vào design amendment.**

  Cập nhật spec dashboard sau Decision Gate 1: labels VI/EN, role của Thêm, visibility Finance/Legal/CRM. Không sửa UI trước khi product owner duyệt.

- [ ] **Step 2: Viết golden tests đỏ.**

  Chụp 1440×1000, 1024×768, 768×1024, 390×844. Assert header không overflow; first viewport desktop có queue và top priorities; mobile một cột; chat không che CTA; modal không vượt viewport.

- [ ] **Step 3: Tách primitives visual.**

  Đưa spacing, typography, surface/border/elevation và semantic color vào AppTheme. HubSectionHeader/HubStatusSurface chỉ đọc token; bỏ hard-coded indigo trong Hub. Green chỉ dùng verified success; amber pending; red unavailable/risk.

- [ ] **Step 4: Sắp lại nội dung.**

  Hôm nay: context header → pulse → cần bạn xử lý → 3 ưu tiên → Co-Founder/chat. Workforce tách rõ quản lý AI. Không tạo Dashboard route thứ hai; /dashboard giữ alias compatibility tới /hub.

- [ ] **Step 5: Loại mock drift sau khi thay test.**

  Thay test dùng HologramHubScreen mock bằng HologramHubView thật với fake service. Khi không còn import, xin xác nhận riêng trước khi xóa mock screen/panes.

- [ ] **Step 6: Gate và commits.**

  Run: cd frontend && flutter test test/modules/hologram_hub/hub_responsive_golden_test.dart test/core/shell/app_shell_test.dart test/core/routing/hub_route_test.dart && flutter analyze

  Commits: feat(hub): establish unified dashboard hierarchy; sau approval xóa mock: test(hub): replace retired mock screen

### Task 6: Đóng P0 Vault và tái xác minh authority/durability

**Files:**
- Modify: apps/cosa/api/vault_routes.py
- Modify: apps/cosa/api/vault_schemas.py
- Modify: frontend/lib/modules/vault/models/vault_document.dart
- Modify: frontend/lib/modules/vault/services/vault_service.dart
- Modify: tests/apps/cosa/test_vault_document_routes.py
- Modify: frontend/test/modules/vault/vault_service_test.dart

**Interfaces:**

```text
upload_url: /agent/vault/uploads/{upload_id}/content
upload_token: opaque one-time ticket
header: X-Vault-Upload-Token: {upload_token}
```

  Upload endpoint derives workspace from verified ticket; no workspace_id query input.

- [ ] **Step 1: Viết security tests đỏ.**

  Assert response không có secret=, workspace query hoặc storage path. Upload chỉ succeeds với header token; missing/expired/wrong ticket là generic 404; ticket workspace A không ghi được B.

- [ ] **Step 2: Chạy test đỏ.**

  Run: PYTHONPATH=. .venv/bin/python -m pytest tests/apps/cosa/test_vault_document_routes.py -q

  Expected: fail vì response hiện nhúng secret/workspace vào upload_url.

- [ ] **Step 3: Đổi ticket transport, giữ stream.**

  create_document trả path sạch và token tách riêng. upload_content đọc token header, resolve workspace/upload server-side, chuyển async iterator trực tiếp vào write_upload_stream; không materialize request.stream() thành list.

- [ ] **Step 4: Cập nhật Dart.**

  VaultDocumentUpload thêm uploadToken. uploadContent nhận upload object và truyền header token. Không persist/log URL or token.

- [ ] **Step 5: Reverify các finding đã vá.**

  Run từng lệnh riêng:

```text
make services-test
make apps-cosa-test
make lease-integration-test
make e2e-cross-plane-smoke
```

  Ghi kết quả IMPLEMENTED/WIRED/VERIFIED/BLOCKED. Nếu smoke fail, giữ trace/error code và tạo finding riêng; không đổi assertion để hợp thức hóa 500.

- [ ] **Step 6: Commit.**

  Commit: fix(vault): move upload ticket out of URL query

### Task 7: Finance/legal regime pack sau legal decision

**Files:**
- Modify: services/company/finance-legal/services/accounting-regime-policy.service.ts
- Modify: services/company/finance-legal/services/accounting-reports.service.ts
- Modify: services/company/finance-legal/services/legal-applicability.service.ts
- Modify/Create: services/company/finance-legal/migrations/*
- Modify: services/company/finance-legal/tests/accounting-regime.test.ts
- Modify/Create: report/legal applicability tests cùng service

**Interfaces:**

```ts
resolveAccountingRegime(workspaceId, asOfDate): {
  jurisdiction: string;
  legalEntityScope: string;
  packId: string;
  version: string;
  effectiveFrom: string;
  effectiveTo: string | null;
}
```

- [ ] **Step 1: Chốt legal input.**

  Ghi jurisdiction, entity type, period, document number/year/effective status, owner và approval path. Thiếu một mục thì dừng Task 7; không default TT58/TT99/TT133.

- [ ] **Step 2: Viết tests đỏ.**

  Arbitrary regulationCode không đổi report mapping; pack expired bị reject; tenant A không đọc/activate draft B; report snapshot lưu exact pack version.

- [ ] **Step 3: Implement service rule.**

  Add expand-only migration cho immutable pack/version/applicability. Reports gọi resolver và persist provenance. Legal applicability chỉ trả published/approved source. APIError thay cho silent fallback TT58.

- [ ] **Step 4: Gate và commit.**

  Run: make services-test-company && make company-boundary-check && make encore-handler-boundary-check && make ts-suppression-check

  Nếu có migration: make migration-check && make migration-compat-check && make test-migration-rollback

  Commit: feat(finance): resolve reports from approved regime packs

### Task 8: Release evidence và acceptance cuối

**Files:**
- Modify/Create: docs/architecture/CODEBASE_HARDENING_2026-09-09.md
- Modify: docs/runbooks/truthful-mvp-release-checklist.md
- Regenerate khi input đổi: company usage/route/contract generated artifacts qua target chính thức

- [ ] **Step 1: Chạy gate từng lớp.**

```text
make lint
make typecheck-py
make company-boundary-check
make encore-handler-boundary-check
make ts-suppression-check
make frontend-api-contract-check
make route-auth-allowlist-check
make contract-freeze-check
make frontend-test
make frontend-analyze
make services-test
make apps-cosa-test
make agent-test
make lease-integration-test
make e2e-cross-plane-smoke
```

- [ ] **Step 2: Ghi evidence thật.**

  Mỗi finding cần commit, red/green test, wired path, environment, gate output, migration/rollback nếu có. Điều kiện thiếu infrastructure ghi BLOCKED, không đổi thành pass dựa mock.

- [ ] **Step 3: Manual authenticated UI review.**

  Dùng workspace test không nhạy cảm ở bốn viewport. Duyệt hidden capability, error/retry, empty, workspace switch, VI/EN, approval action. Không dùng credential cá nhân trong automation.

- [ ] **Step 4: Acceptance criteria.**

  - Frontend compile/analyze sạch và full test pass.
  - Hub không biểu diễn failure/unloaded là zero hoặc success.
  - Sidebar, Hub switcher, guard cùng visibility policy.
  - Upload secret không nằm URL/query/log; body streaming.
  - Route frontend có contract; generated inventory đồng bộ.
  - Finance only starts sau legal decision, report có provenance version.
  - Release report phân biệt IMPLEMENTED/WIRED/VERIFIED/BLOCKED.

- [ ] **Step 5: Commit evidence.**

  Commit: docs: record truthful UI remediation evidence

## Dependency and Release Order

```text
Task 1 ─┬─> Task 2 ─┬─> Task 3 ─> Task 4 ─> Task 5
        │           │
        │           └─> Task 6 ────────────────> Task 8
        └──────────────────────────────────────> Task 8
Decision Gate 2 ───────────────────────────────> Task 7 ─> Task 8
```

## Self-Review

- Coverage: build/locale, contract, truthful Hub, visibility UX, IA/design system, Vault, authority/durability evidence, finance/legal regime, and release evidence each map to one task.
- Không tự quyết policy: IA và legal applicability đều có decision gate.
- Generated artifact không hand-edit và không kết luận release từ static test.
