# Hub không sidebar — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Hoàn tất migrate 10 module sidebar còn lại sang route canonical riêng, sửa mọi nơi điều hướng qua index cũ, rồi tách `/hub` khỏi `AppShell` để dùng thẳng `HologramHubView` (đã tồn tại, không sidebar) làm trang Hub.

**Architecture:** Lặp lại đúng pattern của 11 module đã migrate (`WorkspaceModule` enum + `moduleRoutes` list, bọc `AppShell`) cho 10 module còn lại — tái dùng `StrategyBinding` có sẵn cho 5 module thuộc `strategy`, tạo 3 binding nhỏ mới cho phần còn lại. Sau đó sửa `HubCommandMixin.openDashboard()` (điểm trung tâm duy nhất mọi nơi dùng để điều hướng theo index cũ — voice command, vài nút bấm) để trỏ thẳng route canonical. Cuối cùng đổi `GetPage` của `/hub` sang `HologramHubView`, dùng `AppShellController.ensureShellDependencies()` (pattern đã có sẵn, dùng ở `/projects/new`) để đảm bảo controller cần thiết vẫn tồn tại khi không còn `AppShell` bọc ngoài.

**Tech Stack:** Flutter, GetX (Bindings/GetPage/Middleware).

## Global Constraints

- Không thiết kế lại nội dung 10 view đang migrate — chuyển chỗ nguyên trạng (spec §3).
- Không đổi sidebar của 21 module khác — chỉ riêng `/hub` không còn sidebar (spec §2.2).
- Route mới dùng đúng middleware `[AuthMiddleware(), ProjectSetupGuardMiddleware()]` giống 11 module đã migrate, trừ khi phát hiện lý do cụ thể khác (ghi rõ nếu có).
- Không để lại code chết mới — mọi nhánh/switch-case/import không còn dùng phải xoá trong cùng plan này (không hoãn sang "dọn sau").
- Phạm vi dọn dẹp CÓ GIỚI HẠN: chỉ xoá `DashboardView`/`DashboardBinding`/`DashboardContentBody` (xác nhận hết tham chiếu trước khi xoá) và nhánh "legacy index" chết rõ ràng trong `_navigateOrChangePage`. KHÔNG động vào `DashboardController` (sidebar 21 module khác vẫn dùng state khác của nó — stage filtering, demo mode, developer mode, expandedGroupIndex) — nằm ngoài phạm vi spec.

---

## Task 1: 3 Binding mới cho các module chưa có Binding

**Files:**
- Create: `frontend/lib/modules/organization/bindings/organization_binding.dart`
- Create: `frontend/lib/modules/skills/bindings/skill_registry_binding.dart`
- Create: `frontend/lib/modules/workspace_runtime/bindings/workspace_runtime_binding.dart`
- Test: `frontend/test/modules/organization/bindings/organization_binding_test.dart`
- Test: `frontend/test/modules/skills/bindings/skill_registry_binding_test.dart`
- Test: `frontend/test/modules/workspace_runtime/bindings/workspace_runtime_binding_test.dart`

**Interfaces:**
- Consumes: `OrganizationController` (constructor không tham số, `frontend/lib/modules/organization/controllers/organization_controller.dart:7`), `SkillRegistryController` (constructor không tham số, `frontend/lib/modules/skills/controllers/skill_registry_controller.dart:6`), `WorkspaceRuntimeController` (constructor `{WorkspaceRuntimeService? service}`, `frontend/lib/modules/workspace_runtime/controllers/workspace_runtime_controller.dart:6-8`).
- Produces: `OrganizationBinding`, `SkillRegistryBinding`, `WorkspaceRuntimeBinding` — dùng ở Task 2.

- [ ] **Step 1: Viết test trước — mỗi binding đăng ký đúng controller**

```dart
// frontend/test/modules/organization/bindings/organization_binding_test.dart
import 'package:flutter_test/flutter_test.dart';
import 'package:get/get.dart';
import 'package:frontend/modules/organization/bindings/organization_binding.dart';
import 'package:frontend/modules/organization/controllers/organization_controller.dart';

void main() {
  setUp(() {
    Get.reset();
    Get.testMode = true;
  });

  test('registers OrganizationController', () {
    OrganizationBinding().dependencies();
    expect(Get.isRegistered<OrganizationController>(), isTrue);
  });
}
```

```dart
// frontend/test/modules/skills/bindings/skill_registry_binding_test.dart
import 'package:flutter_test/flutter_test.dart';
import 'package:get/get.dart';
import 'package:frontend/modules/skills/bindings/skill_registry_binding.dart';
import 'package:frontend/modules/skills/controllers/skill_registry_controller.dart';

void main() {
  setUp(() {
    Get.reset();
    Get.testMode = true;
  });

  test('registers SkillRegistryController', () {
    SkillRegistryBinding().dependencies();
    expect(Get.isRegistered<SkillRegistryController>(), isTrue);
  });
}
```

```dart
// frontend/test/modules/workspace_runtime/bindings/workspace_runtime_binding_test.dart
import 'package:flutter_test/flutter_test.dart';
import 'package:get/get.dart';
import 'package:frontend/modules/workspace_runtime/bindings/workspace_runtime_binding.dart';
import 'package:frontend/modules/workspace_runtime/controllers/workspace_runtime_controller.dart';

void main() {
  setUp(() {
    Get.reset();
    Get.testMode = true;
  });

  test('registers WorkspaceRuntimeController', () {
    WorkspaceRuntimeBinding().dependencies();
    expect(Get.isRegistered<WorkspaceRuntimeController>(), isTrue);
  });
}
```

- [ ] **Step 2: Chạy 3 test, xác nhận FAIL**

Run: `cd frontend && flutter test test/modules/organization/bindings/ test/modules/skills/bindings/ test/modules/workspace_runtime/bindings/`
Expected: FAIL — 3 file binding chưa tồn tại.

- [ ] **Step 3: Viết 3 binding**

```dart
// frontend/lib/modules/organization/bindings/organization_binding.dart
import 'package:get/get.dart';
import '../controllers/organization_controller.dart';

class OrganizationBinding extends Bindings {
  @override
  void dependencies() {
    Get.lazyPut<OrganizationController>(() => OrganizationController());
  }
}
```

```dart
// frontend/lib/modules/skills/bindings/skill_registry_binding.dart
import 'package:get/get.dart';
import '../controllers/skill_registry_controller.dart';

class SkillRegistryBinding extends Bindings {
  @override
  void dependencies() {
    Get.lazyPut<SkillRegistryController>(() => SkillRegistryController());
  }
}
```

```dart
// frontend/lib/modules/workspace_runtime/bindings/workspace_runtime_binding.dart
import 'package:get/get.dart';
import '../controllers/workspace_runtime_controller.dart';

class WorkspaceRuntimeBinding extends Bindings {
  @override
  void dependencies() {
    Get.lazyPut<WorkspaceRuntimeController>(() => WorkspaceRuntimeController());
  }
}
```

- [ ] **Step 4: Chạy lại test, xác nhận PASS**

Run: `cd frontend && flutter test test/modules/organization/bindings/ test/modules/skills/bindings/ test/modules/workspace_runtime/bindings/`
Expected: PASS.

- [ ] **Step 5: `dart analyze` sạch**

Run: `cd frontend && dart analyze lib/modules/organization/ lib/modules/skills/ lib/modules/workspace_runtime/`
Expected: No issues found.

- [ ] **Step 6: Commit**

```bash
cd /Volumes/SSD/javis-saas
git add frontend/lib/modules/organization/bindings/organization_binding.dart \
  frontend/lib/modules/skills/bindings/skill_registry_binding.dart \
  frontend/lib/modules/workspace_runtime/bindings/workspace_runtime_binding.dart \
  frontend/test/modules/organization/bindings/organization_binding_test.dart \
  frontend/test/modules/skills/bindings/skill_registry_binding_test.dart \
  frontend/test/modules/workspace_runtime/bindings/workspace_runtime_binding_test.dart
git commit -m "feat(routing): them 3 Binding con thieu cho migrate module tiep theo

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

## Task 2: Migrate 10 module sang route canonical

**Files:**
- Modify: `frontend/lib/core/routing/module_routes.dart`
- Modify: `frontend/test/core/routing/module_routes_test.dart`

**Interfaces:**
- Consumes: `OrganizationBinding`, `SkillRegistryBinding`, `WorkspaceRuntimeBinding` (Task 1); `StrategyBinding` (đã tồn tại, `frontend/lib/modules/strategy/bindings/strategy_binding.dart`); 10 view class đã tồn tại (`OrganizationView`, `SkillRegistryView`, `OkrsView`, `TwelveWeekYearView`, `ProjectRoadmapView`, `TemplateLibraryView`, `ProjectFundingView`, `NeedsYouView`, `BlockedWorkView`, `WorkInspectorView`).
- Produces: 10 giá trị `WorkspaceModule` mới, 10 dòng mới trong `legacyDashboardIndexForModule`, 10 `GetPage` mới trong `moduleRoutes` — dùng ở Task 3, 5.

Ánh xạ index → module → path → binding (đã xác nhận qua code, không đoán —
`Get.put(XController())` inline trong từng view, không cần Binding riêng cho
5 module `strategy`, tái dùng `StrategyBinding` sẵn có):

| Index | Enum value | Path | View | Binding |
|---|---|---|---|---|
| 19 | `organization` | `/work/organization` | `OrganizationView` | `OrganizationBinding` |
| 24 | `needsYou` | `/work/needsYou` | `NeedsYouView` | `WorkspaceRuntimeBinding` |
| 25 | `blockedWork` | `/work/blockedWork` | `BlockedWorkView` | `WorkspaceRuntimeBinding` |
| 26 | `workInspector` | `/work/workInspector` | `WorkInspectorView` | `WorkspaceRuntimeBinding` |
| 27 | `okrs` | `/work/okrs` | `OkrsView` | `StrategyBinding` |
| 28 | `twelveWy` | `/work/twelveWy` | `TwelveWeekYearView` | `StrategyBinding` |
| 29 | `projectRoadmap` | `/work/projectRoadmap` | `ProjectRoadmapView` | `StrategyBinding` |
| 30 | `templateLibrary` | `/work/templateLibrary` | `TemplateLibraryView` | `StrategyBinding` |
| 32 | `projectFunding` | `/work/projectFunding` | `ProjectFundingView` | `StrategyBinding` |
| 33 | `skillRegistry` | `/work/skillRegistry` | `SkillRegistryView` | `SkillRegistryBinding` |

- [ ] **Step 1: Sửa test trước — thêm assertion cho 10 module mới (sẽ FAIL vì module chưa tồn tại)**

Sửa `frontend/test/core/routing/module_routes_test.dart`:

1. Đổi dòng cuối (hiện đang chứng minh OKRs CHƯA migrate — nay phải đổi nghĩa):

```dart
  test('moduleForLegacyIndex trả về đúng module cho các index sidebar đã migrate', () {
    expect(moduleForLegacyIndex(1), WorkspaceModule.tasks);
    expect(moduleForLegacyIndex(6), WorkspaceModule.approvals);
    expect(moduleForLegacyIndex(19), WorkspaceModule.organization);
    expect(moduleForLegacyIndex(24), WorkspaceModule.needsYou);
    expect(moduleForLegacyIndex(25), WorkspaceModule.blockedWork);
    expect(moduleForLegacyIndex(26), WorkspaceModule.workInspector);
    expect(moduleForLegacyIndex(27), WorkspaceModule.okrs);
    expect(moduleForLegacyIndex(28), WorkspaceModule.twelveWy);
    expect(moduleForLegacyIndex(29), WorkspaceModule.projectRoadmap);
    expect(moduleForLegacyIndex(30), WorkspaceModule.templateLibrary);
    expect(moduleForLegacyIndex(32), WorkspaceModule.projectFunding);
    expect(moduleForLegacyIndex(33), WorkspaceModule.skillRegistry);
    // Index 0 (hub) không có module canonical riêng — hub CHÍNH LÀ route
    // đang chứa danh sách sidebar này.
    expect(moduleForLegacyIndex(0), isNull);
  });
```

(Test `'every WorkspaceModule (trừ hub) có đúng một route canonical được guard'` đã có sẵn dạng vòng lặp qua `WorkspaceModule.values` — TỰ ĐỘNG phủ 10 module mới, không cần sửa gì thêm ở đó.)

- [ ] **Step 2: Chạy test, xác nhận FAIL**

Run: `cd frontend && flutter test test/core/routing/module_routes_test.dart`
Expected: FAIL — `WorkspaceModule.organization` (và 9 giá trị khác) chưa tồn tại, lỗi biên dịch.

- [ ] **Step 3: Thêm 10 giá trị vào `enum WorkspaceModule`**

Sửa `frontend/lib/core/routing/module_routes.dart` dòng 45-58, thêm vào cuối enum (trước dấu `}`):

```dart
enum WorkspaceModule {
  hub,
  tasks,
  approvals,
  strategy,
  agents,
  vault,
  sales,
  marketing,
  finance,
  legal,
  workflows,
  settings,
  organization,
  needsYou,
  blockedWork,
  workInspector,
  okrs,
  twelveWy,
  projectRoadmap,
  templateLibrary,
  projectFunding,
  skillRegistry,
}
```

- [ ] **Step 4: Thêm 10 dòng vào `legacyDashboardIndexForModule`**

Sửa dòng 92-104, thêm vào cuối map (trước dấu `};`):

```dart
const Map<WorkspaceModule, int> legacyDashboardIndexForModule = {
  WorkspaceModule.tasks: 1,
  WorkspaceModule.vault: 2,
  WorkspaceModule.strategy: 3,
  WorkspaceModule.workflows: 5,
  WorkspaceModule.approvals: 6,
  WorkspaceModule.agents: 7,
  WorkspaceModule.settings: 13,
  WorkspaceModule.marketing: 17,
  WorkspaceModule.finance: 21,
  WorkspaceModule.legal: 22,
  WorkspaceModule.sales: 23,
  WorkspaceModule.organization: 19,
  WorkspaceModule.needsYou: 24,
  WorkspaceModule.blockedWork: 25,
  WorkspaceModule.workInspector: 26,
  WorkspaceModule.okrs: 27,
  WorkspaceModule.twelveWy: 28,
  WorkspaceModule.projectRoadmap: 29,
  WorkspaceModule.templateLibrary: 30,
  WorkspaceModule.projectFunding: 32,
  WorkspaceModule.skillRegistry: 33,
};
```

- [ ] **Step 5: Thêm import cho 10 view + 3 binding mới, thêm 10 `GetPage` vào `moduleRoutes`**

Thêm vào đầu `module_routes.dart` (cạnh các import view/binding hiện có, dòng 17-38):

```dart
import '../../modules/organization/bindings/organization_binding.dart';
import '../../modules/organization/views/organization_view.dart';
import '../../modules/skills/bindings/skill_registry_binding.dart';
import '../../modules/skills/views/skill_registry_view.dart';
import '../../modules/strategy/views/okrs_view.dart';
import '../../modules/strategy/views/project_funding_view.dart';
import '../../modules/strategy/views/project_roadmap_view.dart';
import '../../modules/strategy/views/template_library_view.dart';
import '../../modules/strategy/views/twelve_week_year_view.dart';
import '../../modules/workspace_runtime/bindings/workspace_runtime_binding.dart';
import '../../modules/workspace_runtime/views/blocked_work_view.dart';
import '../../modules/workspace_runtime/views/needs_you_view.dart';
import '../../modules/workspace_runtime/views/work_inspector_view.dart';
```

Thêm vào cuối `moduleRoutes` (trước dấu `];` ở dòng 217):

```dart
  GetPage(
    name: WorkspaceModule.organization.path,
    page: () => const AppShell(activeModule: WorkspaceModule.organization, child: OrganizationView()),
    binding: OrganizationBinding(),
    middlewares: [AuthMiddleware(), ProjectSetupGuardMiddleware()],
  ),
  GetPage(
    name: WorkspaceModule.needsYou.path,
    page: () => const AppShell(activeModule: WorkspaceModule.needsYou, child: NeedsYouView()),
    binding: WorkspaceRuntimeBinding(),
    middlewares: [AuthMiddleware(), ProjectSetupGuardMiddleware()],
  ),
  GetPage(
    name: WorkspaceModule.blockedWork.path,
    page: () => const AppShell(activeModule: WorkspaceModule.blockedWork, child: BlockedWorkView()),
    binding: WorkspaceRuntimeBinding(),
    middlewares: [AuthMiddleware(), ProjectSetupGuardMiddleware()],
  ),
  GetPage(
    name: WorkspaceModule.workInspector.path,
    page: () => const AppShell(activeModule: WorkspaceModule.workInspector, child: WorkInspectorView()),
    binding: WorkspaceRuntimeBinding(),
    middlewares: [AuthMiddleware(), ProjectSetupGuardMiddleware()],
  ),
  GetPage(
    name: WorkspaceModule.okrs.path,
    page: () => const AppShell(activeModule: WorkspaceModule.okrs, child: OkrsView()),
    binding: StrategyBinding(),
    middlewares: [AuthMiddleware(), ProjectSetupGuardMiddleware()],
  ),
  GetPage(
    name: WorkspaceModule.twelveWy.path,
    page: () => const AppShell(activeModule: WorkspaceModule.twelveWy, child: TwelveWeekYearView()),
    binding: StrategyBinding(),
    middlewares: [AuthMiddleware(), ProjectSetupGuardMiddleware()],
  ),
  GetPage(
    name: WorkspaceModule.projectRoadmap.path,
    page: () => const AppShell(activeModule: WorkspaceModule.projectRoadmap, child: ProjectRoadmapView()),
    binding: StrategyBinding(),
    middlewares: [AuthMiddleware(), ProjectSetupGuardMiddleware()],
  ),
  GetPage(
    name: WorkspaceModule.templateLibrary.path,
    page: () => const AppShell(activeModule: WorkspaceModule.templateLibrary, child: TemplateLibraryView()),
    binding: StrategyBinding(),
    middlewares: [AuthMiddleware(), ProjectSetupGuardMiddleware()],
  ),
  GetPage(
    name: WorkspaceModule.projectFunding.path,
    page: () => const AppShell(activeModule: WorkspaceModule.projectFunding, child: ProjectFundingView()),
    binding: StrategyBinding(),
    middlewares: [AuthMiddleware(), ProjectSetupGuardMiddleware()],
  ),
  GetPage(
    name: WorkspaceModule.skillRegistry.path,
    page: () => const AppShell(activeModule: WorkspaceModule.skillRegistry, child: SkillRegistryView()),
    binding: SkillRegistryBinding(),
    middlewares: [AuthMiddleware(), ProjectSetupGuardMiddleware()],
  ),
```

`StrategyBinding` cần import `frontend/lib/modules/strategy/bindings/strategy_binding.dart` — đã có sẵn trong file (dùng cho route `strategy` hiện tại), không cần thêm.

- [ ] **Step 6: Chạy lại test, xác nhận PASS**

Run: `cd frontend && flutter test test/core/routing/module_routes_test.dart`
Expected: PASS (toàn bộ, kể cả vòng lặp "every WorkspaceModule" tự động phủ 10 module mới).

- [ ] **Step 7: `dart analyze` sạch**

Run: `cd frontend && dart analyze lib/core/routing/`
Expected: No issues found.

- [ ] **Step 8: Commit**

```bash
cd /Volumes/SSD/javis-saas
git add frontend/lib/core/routing/module_routes.dart \
  frontend/test/core/routing/module_routes_test.dart
git commit -m "feat(routing): migrate 10 module con lai (OKRs, 12WY, Du an...) sang route canonical

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

## Task 3: Xoá switch-case chết trong `DashboardContentBody`

**Files:**
- Modify: `frontend/lib/modules/dashboard/views/widgets/dashboard_content_body.dart`

**Interfaces:**
- Consumes: `moduleForLegacyIndex` (từ Task 2, giờ trả về non-null cho MỌI index trừ 0).

- [ ] **Step 1: Xoá 10 case đã migrate + import không còn dùng**

Sửa `frontend/lib/modules/dashboard/views/widgets/dashboard_content_body.dart`:
xoá các dòng import (dòng 8-17) cho 10 view đã migrate:

```dart
import '../../../organization/views/organization_view.dart';
import '../../../skills/views/skill_registry_view.dart';
import '../../../strategy/views/okrs_view.dart';
import '../../../strategy/views/project_funding_view.dart';
import '../../../strategy/views/project_roadmap_view.dart';
import '../../../strategy/views/template_library_view.dart';
import '../../../strategy/views/twelve_week_year_view.dart';
import '../../../workspace_runtime/views/blocked_work_view.dart';
import '../../../workspace_runtime/views/needs_you_view.dart';
import '../../../workspace_runtime/views/work_inspector_view.dart';
```

Sửa `switch (index)` (dòng 86-111) — xoá 10 case, chỉ còn:

```dart
    switch (index) {
      case 0:
        return const HologramHubView();
      default:
        return const HologramHubView();
    }
```

Cập nhật lại docblock ở đầu file (dòng 21-32) — bỏ câu "hiện tại còn ~10 mục... chưa có route riêng", thay bằng ghi chú switch giờ chỉ còn case 0 (mọi module khác đã có route canonical, redirect adapter phía trên xử lý hết) và sẽ được xoá hẳn cùng lúc với `DashboardContentBody` ở Task 6.

- [ ] **Step 2: `dart analyze` sạch (bắt import thừa/case không dùng)**

Run: `cd frontend && dart analyze lib/modules/dashboard/`
Expected: No issues found — nếu còn cảnh báo unused import, xoá nốt.

- [ ] **Step 3: Chạy lại toàn bộ test hiện có của dashboard để không có regression**

Run: `cd frontend && flutter test test/modules/dashboard/ test/modules/hologram_hub/`
Expected: Tất cả test hiện có vẫn PASS (không có test nào assert vào 10 case vừa xoá — nếu có, đó là dấu hiệu cần dừng lại và hỏi, không tự xoá test).

- [ ] **Step 4: Commit**

```bash
cd /Volumes/SSD/javis-saas
git add frontend/lib/modules/dashboard/views/widgets/dashboard_content_body.dart
git commit -m "chore(dashboard): xoa 10 switch-case da co route canonical rieng khoi DashboardContentBody

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

## Task 4: Module switcher overlay trong `HologramHubView`

**Files:**
- Modify: `frontend/lib/modules/hologram_hub/views/hologram_hub_view.dart`
- Test: `frontend/test/modules/hologram_hub/hologram_hub_view_module_switcher_test.dart`

**Interfaces:**
- Consumes: `DashboardNavConfig.coreNavGroups` (`frontend/lib/modules/dashboard/models/dashboard_nav_config.dart`), `moduleForLegacyIndex` (`frontend/lib/core/routing/module_routes.dart`, từ Task 2 trả về non-null cho mọi index thật).
- Produces: hàm private `_openModuleSwitcher(BuildContext context)` trong `HologramHubView` — không export, chỉ dùng nội bộ view này.

- [ ] **Step 1: Viết test trước — bấm icon menu mở overlay, bấm 1 mục điều hướng đúng route**

```dart
// frontend/test/modules/hologram_hub/hologram_hub_view_module_switcher_test.dart
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:get/get.dart';
import 'package:frontend/core/shell/app_shell_controller.dart';
import 'package:frontend/modules/hologram_hub/views/hologram_hub_view.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() {
    Get.reset();
    Get.testMode = true;
    AppShellController.ensureShellDependencies();
  });

  testWidgets('tapping the menu icon opens a module list with OKRs entry', (
    tester,
  ) async {
    await tester.pumpWidget(
      const GetMaterialApp(home: Scaffold(body: HologramHubView())),
    );
    await tester.pump();

    await tester.tap(find.byTooltip('Chuyển module'));
    await tester.pumpAndSettle();

    expect(find.text('OKRs'), findsOneWidget);
    expect(find.text('Dự án'), findsOneWidget);
  });
}
```

- [ ] **Step 2: Chạy test, xác nhận FAIL**

Run: `cd frontend && flutter test test/modules/hologram_hub/hologram_hub_view_module_switcher_test.dart`
Expected: FAIL — không có widget nào với tooltip "Chuyển module".

- [ ] **Step 3: Thêm icon menu + overlay vào `HologramHubView`**

Thêm import vào đầu `frontend/lib/modules/hologram_hub/views/hologram_hub_view.dart`:

```dart
import '../../dashboard/models/dashboard_nav_config.dart';
import '../../../core/routing/module_routes.dart';
```

Thêm 1 `IconButton` mới NGAY TRƯỚC "Dashboard Button" hiện có (trước dòng 247-262):

```dart
                      // Module Switcher — thay cho sidebar không còn ở Hub
                      IconButton(
                        onPressed: () => _openModuleSwitcher(context),
                        icon: const Icon(
                          Icons.apps_rounded,
                          color: Colors.white70,
                          size: 20,
                        ),
                        tooltip: 'Chuyển module',
                        padding: EdgeInsets.zero,
                        constraints: const BoxConstraints(
                          minWidth: 36,
                          minHeight: 36,
                        ),
                      ),
                      const SizedBox(width: 4),
```

Thêm method mới vào cuối class `_HologramHubViewState`/`HologramHubView` (cạnh `_openChatBottomSheet`):

```dart
  void _openModuleSwitcher(BuildContext context) {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (ctx) {
        return Container(
          height: MediaQuery.of(context).size.height * 0.7,
          decoration: const BoxDecoration(
            color: Color(0xFF0F172A),
            borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
          ),
          padding: const EdgeInsets.all(20),
          child: ListView(
            children: DashboardNavConfig.coreNavGroups.expand((group) {
              return [
                Padding(
                  padding: const EdgeInsets.only(top: 12, bottom: 6),
                  child: Text(
                    group.title,
                    style: const TextStyle(
                      color: Colors.white54,
                      fontSize: 12,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ),
                ...group.items.map((item) {
                  final module = moduleForLegacyIndex(item.index);
                  return ListTile(
                    leading: Icon(item.icon, color: Colors.white70),
                    title: Text(item.label, style: const TextStyle(color: Colors.white)),
                    onTap: module == null
                        ? null
                        : () {
                            Navigator.pop(ctx);
                            Get.toNamed(module.path);
                          },
                  );
                }),
              ];
            }).toList(),
          ),
        );
      },
    );
  }
```

Đã xác nhận: `HologramHubView extends StatelessWidget` và `_openChatBottomSheet`
là method trực tiếp của class này (không phải của 1 State riêng) — thêm
`_openModuleSwitcher` cùng cấp, ngay dưới `_openChatBottomSheet`.

- [ ] **Step 4: Chạy lại test, xác nhận PASS**

Run: `cd frontend && flutter test test/modules/hologram_hub/hologram_hub_view_module_switcher_test.dart`
Expected: PASS.

- [ ] **Step 5: `dart analyze` sạch, chạy lại toàn bộ test hologram_hub hiện có**

Run: `cd frontend && dart analyze lib/modules/hologram_hub/ && flutter test test/modules/hologram_hub/`
Expected: No issues found; tất cả test PASS (không regression).

- [ ] **Step 6: Commit**

```bash
cd /Volumes/SSD/javis-saas
git add frontend/lib/modules/hologram_hub/views/hologram_hub_view.dart \
  frontend/test/modules/hologram_hub/hologram_hub_view_module_switcher_test.dart
git commit -m "feat(hub): them module switcher overlay thay the sidebar cho HologramHubView

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

## Task 5: Sửa `openDashboard()` dùng route canonical thay vì index cũ

**Files:**
- Modify: `frontend/lib/modules/hologram_hub/controllers/mixins/hub_command_mixin.dart`
- Test: `frontend/test/modules/hologram_hub/controllers/mixins/hub_command_mixin_open_dashboard_test.dart`

**Interfaces:**
- Consumes: `moduleForLegacyIndex`, `WorkspaceModule` (Task 2, `frontend/lib/core/routing/module_routes.dart`), `AppRoutes.hub` (`frontend/lib/core/routing/app_routes.dart`).
- Produces: `resolveLegacyDashboardTarget(int targetTab)` (hàm top-level thuần, thêm vào `module_routes.dart`) — dùng bởi `openDashboard()`.

**Bối cảnh:** `openDashboard()` hiện gọi `DashboardController.changePage()` rồi
`Get.toNamed(AppRoutes.dashboard)` (redirect vào `/hub`), dựa vào
`DashboardContentBody` đọc lại `currentIndex` để hiển thị đúng view. Dùng bởi
voice navigation (`hub_voice_mixin.dart:123-158`), `onSettingsPressed`,
`openStrategyNextActions`, `openOkrs`, `openTwelveWeekYear`
(`hub_command_mixin.dart:350-353`), và 2 widget khác
(`funding_readiness_card.dart:153`, `hub_chat_header.dart:124`). Sau Task 6
(xoá `DashboardContentBody`), cơ chế này sẽ không còn hoạt động — phải sửa
TRƯỚC khi flip route.

- [ ] **Step 1: Viết test trước cho `resolveLegacyDashboardTarget`**

```dart
// frontend/test/core/routing/module_routes_test.dart — thêm test mới vào file đã có
test('resolveLegacyDashboardTarget maps legacy index to canonical path, falls back to hub', () {
  expect(resolveLegacyDashboardTarget(27), '/work/okrs');
  expect(resolveLegacyDashboardTarget(28), '/work/twelveWy');
  expect(resolveLegacyDashboardTarget(1), '/work/tasks');
  expect(resolveLegacyDashboardTarget(0), '/hub');
});
```

- [ ] **Step 2: Chạy test, xác nhận FAIL**

Run: `cd frontend && flutter test test/core/routing/module_routes_test.dart`
Expected: FAIL — `resolveLegacyDashboardTarget` chưa tồn tại.

- [ ] **Step 3: Thêm `resolveLegacyDashboardTarget` vào `module_routes.dart`**

Thêm ngay sau hàm `moduleForLegacyIndex` (dòng 108-113):

```dart
/// Trả về path canonical cho 1 "target tab" kiểu cũ — dùng bởi
/// `HubCommandMixin.openDashboard()` sau khi mọi module sidebar đã có route
/// riêng (Task "Hub không sidebar"). `targetTab` không map được (0 = hub, hoặc
/// bất kỳ giá trị lạ nào) trả về `AppRoutes.hub` — Hub chính là "index 0".
String resolveLegacyDashboardTarget(int targetTab) {
  final module = moduleForLegacyIndex(targetTab);
  return module?.path ?? AppRoutes.hub;
}
```

- [ ] **Step 4: Chạy lại test, xác nhận PASS**

Run: `cd frontend && flutter test test/core/routing/module_routes_test.dart`
Expected: PASS.

- [ ] **Step 5: Sửa `openDashboard()` để dùng hàm mới**

Sửa `frontend/lib/modules/hologram_hub/controllers/mixins/hub_command_mixin.dart`,
thêm import:

```dart
import '../../../../core/routing/module_routes.dart';
```

Sửa hàm `openDashboard` (dòng 356-362):

```dart
  void openDashboard([int targetTab = 0, int groupIndex = 0, int strategySubTab = 0]) {
    // `groupIndex`/`strategySubTab` không còn dùng sau khi mọi module có
    // route canonical riêng (trước đây truyền cho `DashboardController.
    // changePage` để chọn đúng tab/group hiển thị trong `DashboardContentBody`
    // — nay điều hướng thẳng bằng route, không qua state `currentIndex` nữa).
    // Giữ nguyên chữ ký hàm để không phải sửa 6+ call site đang gọi nó.
    Get.toNamed(resolveLegacyDashboardTarget(targetTab));
  }
```

- [ ] **Step 6: Viết test xác nhận `openDashboard` điều hướng đúng route cho các call site thật đang dùng (27=OKRs, 28=12WY, 1=Tasks)**

```dart
// frontend/test/modules/hologram_hub/controllers/mixins/hub_command_mixin_open_dashboard_test.dart
import 'package:flutter_test/flutter_test.dart';
import 'package:get/get.dart';
import 'package:frontend/core/routing/module_routes.dart';

void main() {
  setUp(() {
    Get.reset();
    Get.testMode = true;
  });

  test('resolveLegacyDashboardTarget covers every call site used by HubCommandMixin/HubVoiceMixin', () {
    // Xem hub_voice_mixin.dart:123-158 và hub_command_mixin.dart:350-353 —
    // các targetTab thật đang được gọi trong codebase.
    final usedTargetTabs = {1, 3, 24, 25, 26, 27, 28, 0, 13};
    for (final tab in usedTargetTabs) {
      final path = resolveLegacyDashboardTarget(tab);
      expect(path, isNotEmpty);
      expect(path == '/hub' || path.startsWith('/work/'), isTrue,
          reason: 'targetTab $tab phải map ra 1 route hợp lệ, nhận được "$path"');
    }
  });
}
```

- [ ] **Step 7: Chạy test, xác nhận PASS**

Run: `cd frontend && flutter test test/modules/hologram_hub/controllers/mixins/hub_command_mixin_open_dashboard_test.dart`
Expected: PASS.

- [ ] **Step 8: `dart analyze` sạch, chạy lại toàn bộ test hologram_hub**

Run: `cd frontend && dart analyze lib/modules/hologram_hub/ lib/core/routing/ && flutter test test/modules/hologram_hub/ test/core/routing/`
Expected: No issues found; tất cả test PASS.

- [ ] **Step 9: Commit**

```bash
cd /Volumes/SSD/javis-saas
git add frontend/lib/core/routing/module_routes.dart \
  frontend/lib/modules/hologram_hub/controllers/mixins/hub_command_mixin.dart \
  frontend/test/core/routing/module_routes_test.dart \
  frontend/test/modules/hologram_hub/controllers/mixins/hub_command_mixin_open_dashboard_test.dart
git commit -m "fix(hub): openDashboard() dieu huong bang route canonical thay vi index cu

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

## Task 6: Flip `/hub` sang `HologramHubView`, xoá code chết

**Files:**
- Modify: `frontend/lib/core/routing/app_pages.dart`
- Modify: `frontend/lib/modules/dashboard/views/widgets/dashboard_sidebar.dart`
- Delete: `frontend/lib/modules/dashboard/views/dashboard_view.dart`
- Delete: `frontend/lib/modules/dashboard/bindings/dashboard_binding.dart`
- Delete: `frontend/lib/modules/dashboard/views/widgets/dashboard_content_body.dart`
- Test: `frontend/test/core/routing/hub_route_test.dart`

**Interfaces:**
- Consumes: `AppShellController.ensureShellDependencies()` (đã tồn tại, `frontend/lib/core/shell/app_shell_controller.dart:27-44`, pattern giống hệt cách `/projects/new` đang dùng — `frontend/lib/core/routing/app_pages.dart:60-68`).

- [ ] **Step 1: Xác nhận không còn tham chiếu nào khác tới 3 file sẽ xoá**

Run: `cd frontend && grep -rn "DashboardView\b" lib/ && grep -rn "DashboardBinding\b" lib/ && grep -rn "DashboardContentBody\b" lib/`
Expected: chỉ còn xuất hiện ở chính định nghĩa của chúng và ở
`app_pages.dart` (nơi sẽ sửa ở Step 2). Nếu thấy tham chiếu khác (vd 1 test
file import `DashboardView` trực tiếp), DỪNG LẠI — báo cáo, không tự xoá test
đó, hỏi người review trước khi tiếp tục.

- [ ] **Step 2: Viết test trước — `/hub` trỏ tới `HologramHubView`, không phải `DashboardView`**

```dart
// frontend/test/core/routing/hub_route_test.dart
import 'package:flutter_test/flutter_test.dart';
import 'package:get/get.dart';
import 'package:frontend/core/routing/app_pages.dart';
import 'package:frontend/core/routing/app_routes.dart';
import 'package:frontend/modules/hologram_hub/views/hologram_hub_view.dart';

void main() {
  test('/hub route builds HologramHubView directly, not wrapped in AppShell', () {
    final hubPage = AppPages.routes.firstWhere((p) => p.name == AppRoutes.hub);
    final widget = hubPage.page();
    expect(widget, isA<HologramHubView>());
  });
}
```

Đã xác nhận: danh sách route là `static final routes` trên class `AppPages`
(`frontend/lib/core/routing/app_pages.dart:29-32`), không phải biến top-level
— dùng `AppPages.routes` như trên.

- [ ] **Step 3: Chạy test, xác nhận FAIL**

Run: `cd frontend && flutter test test/core/routing/hub_route_test.dart`
Expected: FAIL — `/hub` hiện trả về `DashboardView`, không phải `HologramHubView`.

- [ ] **Step 4: Sửa `GetPage` của `/hub`**

Sửa `frontend/lib/core/routing/app_pages.dart` (dòng 94-99), từ:

```dart
    GetPage(
      name: AppRoutes.hub,
      page: () => const DashboardView(),
      binding: DashboardBinding(),
      middlewares: [AuthMiddleware(), ProjectSetupGuardMiddleware()],
    ),
```

thành:

```dart
    GetPage(
      name: AppRoutes.hub,
      page: () => const HologramHubView(),
      binding: BindingsBuilder(() {
        AppShellController.ensureShellDependencies();
      }),
      middlewares: [AuthMiddleware(), ProjectSetupGuardMiddleware()],
    ),
```

Xoá 2 import không còn dùng (`dashboard_view.dart`, `dashboard_binding.dart`)
ở đầu file, thêm import `HologramHubView` và `AppShellController` (kiểm tra
`AppShellController` đã import chưa — `/projects/new` GetPage đã dùng nó,
khả năng cao đã có sẵn import).

- [ ] **Step 5: Chạy lại test, xác nhận PASS**

Run: `cd frontend && flutter test test/core/routing/hub_route_test.dart`
Expected: PASS.

- [ ] **Step 6: Xoá 3 file dead code**

```bash
cd /Volumes/SSD/javis-saas/frontend
git rm lib/modules/dashboard/views/dashboard_view.dart
git rm lib/modules/dashboard/bindings/dashboard_binding.dart
git rm lib/modules/dashboard/views/widgets/dashboard_content_body.dart
```

- [ ] **Step 7: Xoá nhánh "legacy index" chết trong `dashboard_sidebar.dart`**

Sửa `_navigateOrChangePage` (`frontend/lib/modules/dashboard/views/widgets/dashboard_sidebar.dart:25-40`)
— sau Task 2, MỌI index trong `DashboardNavConfig.allNavItems` đều có
`moduleForLegacyIndex` trả về non-null, nên nhánh `else` (gọi `changePage` +
`Get.offNamed(AppRoutes.hub)`) không bao giờ còn chạy tới. Đơn giản hoá:

```dart
void _navigateOrChangePage(DashboardController controller, int index, int groupIndex) {
  final module = moduleForLegacyIndex(index);
  if (module != null) {
    Get.toNamed(module.path);
    return;
  }
  // Không còn index nào thiếu route sau khi migrate xong — nhánh này chỉ
  // còn là fallback phòng thủ (index lạ không có trong DashboardNavConfig).
  controller.changePage(index, groupIndex);
}
```

Xoá comment cũ ở trên hàm (dòng 11-24) nói về việc cần `changePage` cho "mục
chưa migrate" — không còn đúng nữa, thay bằng 1 dòng ngắn giải thích trạng
thái mới.

- [ ] **Step 8: `dart analyze` sạch toàn bộ frontend**

Run: `cd frontend && dart analyze lib/`
Expected: No issues found — đặc biệt không còn cảnh báo unused import ở
`app_pages.dart`, `dashboard_sidebar.dart`.

- [ ] **Step 9: Chạy toàn bộ test suite liên quan — dashboard, hologram_hub, routing**

Run: `cd frontend && flutter test test/core/routing/ test/modules/dashboard/ test/modules/hologram_hub/`
Expected: Tất cả PASS. Nếu có test cũ nào import trực tiếp `DashboardView`/
`DashboardBinding`/`DashboardContentBody` (đã xoá), sửa/xoá đúng test đó theo
tinh thần "không còn đối tượng để test" — không viết lại test giả để né lỗi.

- [ ] **Step 10: Commit**

```bash
cd /Volumes/SSD/javis-saas
git add frontend/lib/core/routing/app_pages.dart \
  frontend/lib/modules/dashboard/views/widgets/dashboard_sidebar.dart \
  frontend/test/core/routing/hub_route_test.dart
git commit -m "feat(hub): /hub gio la HologramHubView truc tiep, khong con AppShell/sidebar

Xoa DashboardView/DashboardBinding/DashboardContentBody (het tham chieu
sau khi 10 module cuoi cung migrate xong o task truoc) va nhanh legacy-
index chet trong dashboard_sidebar.dart.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```
