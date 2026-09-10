// Task 9 — nguồn sự thật DUY NHẤT cho danh sách "module workspace" hiển thị
// trong sidebar/topbar. Trước task này, `DashboardContentBody` chọn view
// bằng một index nguyên tuỳ tiện (0, 1, 2, ...) không thể deep-link, không
// back-stack thật, không guard riêng từng mục — mọi thứ đều đi qua CÙNG một
// route `/dashboard`. `WorkspaceModule` + `moduleRoutes` thay "authority" đó
// bằng route path canonical thật: mỗi module có ĐÚNG MỘT path, được guard
// bởi `AuthMiddleware`, có back-stack thật của GetX Navigator.
import 'package:flutter/widgets.dart';
import 'package:get/get.dart';

import '../services/module_visibility_controller.dart';
import '../services/workspace_capability_manifest_model.dart';
import '../shell/app_shell.dart';
import '../widgets/surface_state_view.dart';
import 'app_routes.dart';
import 'auth_middleware.dart';
import 'project_setup_guard_middleware.dart';

import '../../modules/automation/bindings/automation_binding.dart';
import '../../modules/automation/views/automation_library_view.dart';
import '../../modules/finance/bindings/finance_binding.dart';
import '../../modules/finance/views/finance_view.dart';
import '../../modules/settings/bindings/settings_binding.dart';
import '../../modules/settings/views/settings_view.dart';
import '../../modules/strategy/bindings/strategy_binding.dart';
import '../../modules/strategy/views/strategy_view.dart';
import '../../modules/tasks/bindings/tasks_binding.dart';
import '../../modules/tasks/views/tasks_view.dart';

/// 12 module có mặt trong sidebar workspace hiện tại (khớp với các nhóm
/// trong `DashboardNavConfig`). `hub` là entrypoint COSA 5+1 core, giữ
/// nguyên path `/hub` đã có sẵn — các module còn lại đứng dưới namespace
/// `/work/*` để phân biệt rõ với route flat cũ (`/tasks`, `/approvals`...),
/// nay chỉ còn là alias redirect (xem `LegacyModuleRedirectMiddleware`).
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
  automation,
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

extension WorkspaceModuleRoute on WorkspaceModule {
  /// Path canonical DUY NHẤT cho module này.
  String get path {
    if (this == WorkspaceModule.hub) return AppRoutes.hub;
    return '/work/$name';
  }
}

/// Middleware redirect cho các URL cũ (`/tasks`, `/approvals`, `/dashboard`,
/// ...) — vẫn còn tồn tại để không phá deep-link/bookmark cũ, nhưng KHÔNG
/// còn tự render nội dung; luôn nhảy sang route canonical mới.
class LegacyModuleRedirectMiddleware extends GetMiddleware {
  LegacyModuleRedirectMiddleware(this.canonicalPath);

  final String canonicalPath;

  @override
  int? get priority => 0;

  @override
  RouteSettings? redirect(String? route) => RouteSettings(name: canonicalPath);
}

/// Founder Trial R1 — thay `ModuleVisibilityGuardMiddleware`. Chặn deep-link
/// vào một module optional (crm/finance/legal) khi manifest per-workspace nói
/// surface tương ứng KHÔNG live (PLANNED/UNAVAILABLE). Manifest là nguồn
/// routing DUY NHẤT — không còn `ModuleVisibility` cache thứ hai.
class ManifestRouteGuardMiddleware extends GetMiddleware {
  ManifestRouteGuardMiddleware(this.module);

  final WorkspaceModule module;

  @override
  int? get priority => 1;

  @override
  RouteSettings? redirect(String? route) {
    if (!Get.isRegistered<ModuleVisibilityController>()) return null;
    final controller = Get.find<ModuleVisibilityController>();
    if (!controller.isVisible(module)) {
      return const RouteSettings(name: AppRoutes.hub);
    }
    return null;
  }
}

/// Back-compat alias — các route table cũ vẫn tham chiếu tên này.
typedef ModuleVisibilityGuardMiddleware = ManifestRouteGuardMiddleware;

/// Ánh xạ giữa index cũ trong `DashboardNavConfig` và module canonical mới.
/// Ban đầu (Task 9) chỉ phủ một phần module, phần còn lại (OKRs, 12WY,
/// roadmap, template library, project funding, needs-you, blocked-work,
/// work-inspector, organization, skill registry) tạm hiển thị qua
/// `DashboardContentBody`. Từ Task 6 (hub-no-sidebar) `DashboardContentBody`
/// đã bị xoá hẳn — MỌI module trong `DashboardNavConfig` đều có route
/// canonical thật ở dưới đây; map này giờ chỉ còn phục vụ tra cứu
/// index-cũ → module cho các call site còn giữ tham số index kiểu cũ.
///
/// `hub` (index 0) KHÔNG có trong map này: hub chính là route ĐANG chứa
/// danh sách sidebar này, tự điều hướng vào chính nó là vô nghĩa.
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

/// Tra ngược: index sidebar cũ → module canonical (null nếu mục đó chưa
/// migrate).
WorkspaceModule? moduleForLegacyIndex(int index) {
  for (final entry in legacyDashboardIndexForModule.entries) {
    if (entry.value == index) return entry.key;
  }
  return null;
}

/// Trả về path canonical cho 1 "target tab" kiểu cũ — dùng bởi
/// `HubCommandMixin.openDashboard()` sau khi mọi module sidebar đã có route
/// riêng (Task "Hub không sidebar"). `targetTab` không map được (0 = hub, hoặc
/// bất kỳ giá trị lạ nào) trả về `AppRoutes.hub` — Hub chính là "index 0".
String resolveLegacyDashboardTarget(int targetTab) {
  final module = moduleForLegacyIndex(targetTab);
  return module?.path ?? AppRoutes.hub;
}

/// Route thật cho từng module (trừ `hub` — hub dùng route `/hub` sẵn có,
/// lắp ráp trực tiếp trong `app_pages.dart` với `HologramHubView`, không
/// còn `DashboardContentBody` nào để host nữa kể từ Task 6 hub-no-sidebar).
///
/// Mỗi route bọc view HIỆN CÓ (không sửa nội dung/visual) bằng `AppShell`
/// (sidebar/topbar/floating voice/banner) — đúng nguyên tắc Task 9: chỉ
/// chuyển quyền sở hữu chrome, không viết lại widget nghiệp vụ.
/// Founder Trial R1 — route cho một module CHƯA có màn hình MVP: render
/// `SurfaceStateView` PLANNED (roadmap card, không CTA) thay vì mở view legacy.
GetPage _plannedRoute(WorkspaceModule module) => GetPage(
      name: module.path,
      page: () => AppShell(
        activeModule: module,
        child: const SurfaceStateView(
          status: SurfaceStatus.planned,
          child: SizedBox.shrink(),
        ),
      ),
      middlewares: [AuthMiddleware(), ProjectSetupGuardMiddleware()],
    );

final List<GetPage> moduleRoutes = [
  // ── R1 live modules ──
  GetPage(
    name: WorkspaceModule.tasks.path,
    page: () => const AppShell(activeModule: WorkspaceModule.tasks, child: TasksView()),
    binding: TasksBinding(),
    middlewares: [AuthMiddleware(), ProjectSetupGuardMiddleware()],
  ),
  GetPage(
    name: WorkspaceModule.strategy.path,
    page: () => const AppShell(activeModule: WorkspaceModule.strategy, child: StrategyView()),
    binding: StrategyBinding(),
    middlewares: [AuthMiddleware(), ProjectSetupGuardMiddleware()],
  ),
  GetPage(
    name: WorkspaceModule.finance.path,
    page: () => const AppShell(activeModule: WorkspaceModule.finance, child: FinanceView()),
    binding: FinanceBinding(),
    middlewares: [
      AuthMiddleware(),
      ProjectSetupGuardMiddleware(),
      ManifestRouteGuardMiddleware(WorkspaceModule.finance),
    ],
  ),
  GetPage(
    name: WorkspaceModule.settings.path,
    page: () => const AppShell(activeModule: WorkspaceModule.settings, child: SettingsView()),
    binding: SettingsBinding(),
    middlewares: [AuthMiddleware(), ProjectSetupGuardMiddleware()],
  ),

  // COSA Automation MVP — gated on the `automation.library` surface. PLANNED
  // until the automation.* capabilities are enabled + the cross-plane E2E is
  // accepted, so the guard redirects to the hub while rollout is disabled.
  GetPage(
    name: WorkspaceModule.automation.path,
    page: () => const AppShell(
      activeModule: WorkspaceModule.automation,
      child: AutomationLibraryView(),
    ),
    binding: AutomationBinding(),
    middlewares: [
      AuthMiddleware(),
      ProjectSetupGuardMiddleware(),
      ManifestRouteGuardMiddleware(WorkspaceModule.automation),
    ],
  ),

  // ── PLANNED / not-yet-built-for-R1 — deep-link resolves to a roadmap card,
  //    never a legacy cockpit ──
  _plannedRoute(WorkspaceModule.approvals),
  _plannedRoute(WorkspaceModule.agents),
  _plannedRoute(WorkspaceModule.vault),
  _plannedRoute(WorkspaceModule.sales),
  _plannedRoute(WorkspaceModule.marketing),
  _plannedRoute(WorkspaceModule.legal),
  _plannedRoute(WorkspaceModule.workflows),
  _plannedRoute(WorkspaceModule.organization),
  _plannedRoute(WorkspaceModule.needsYou),
  _plannedRoute(WorkspaceModule.blockedWork),
  _plannedRoute(WorkspaceModule.workInspector),
  _plannedRoute(WorkspaceModule.okrs),
  _plannedRoute(WorkspaceModule.twelveWy),
  _plannedRoute(WorkspaceModule.projectRoadmap),
  _plannedRoute(WorkspaceModule.templateLibrary),
  _plannedRoute(WorkspaceModule.projectFunding),
  _plannedRoute(WorkspaceModule.skillRegistry),
];

/// Test helper (Task 9 Step 1) — tra route đã đăng ký theo path, dùng để
/// assert mỗi module có ĐÚNG MỘT route canonical được guard.
List<GetPage> routesFor(String path) => moduleRoutes.where((route) => route.name == path).toList();
