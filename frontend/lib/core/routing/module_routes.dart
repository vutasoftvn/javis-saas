// Task 9 — nguồn sự thật DUY NHẤT cho danh sách "module workspace" hiển thị
// trong sidebar/topbar. Trước task này, `DashboardContentBody` chọn view
// bằng một index nguyên tuỳ tiện (0, 1, 2, ...) không thể deep-link, không
// back-stack thật, không guard riêng từng mục — mọi thứ đều đi qua CÙNG một
// route `/dashboard`. `WorkspaceModule` + `moduleRoutes` thay "authority" đó
// bằng route path canonical thật: mỗi module có ĐÚNG MỘT path, được guard
// bởi `AuthMiddleware`, có back-stack thật của GetX Navigator.
import 'package:flutter/widgets.dart';
import 'package:get/get.dart';

import '../shell/app_shell.dart';
import '../widgets/capability_gated_view.dart';
import 'app_routes.dart';
import 'auth_middleware.dart';
import 'project_setup_guard_middleware.dart';

import '../../modules/agents/bindings/agents_binding.dart';
import '../../modules/agents/views/agents_view.dart';
import '../../modules/approvals/bindings/approvals_binding.dart';
import '../../modules/approvals/views/approvals_view.dart';
import '../../modules/finance/bindings/finance_binding.dart';
import '../../modules/finance/views/finance_view.dart';
import '../../modules/legal/bindings/legal_binding.dart';
import '../../modules/legal/views/legal_view.dart';
import '../../modules/marketing/bindings/marketing_binding.dart';
import '../../modules/marketing/views/marketing_cockpit_view.dart';
import '../../modules/organization/bindings/organization_binding.dart';
import '../../modules/organization/views/organization_view.dart';
import '../../modules/sales/bindings/sales_binding.dart';
import '../../modules/sales/views/sales_view.dart';
import '../../modules/settings/bindings/settings_binding.dart';
import '../../modules/settings/views/settings_view.dart';
import '../../modules/skills/bindings/skill_registry_binding.dart';
import '../../modules/skills/views/skill_registry_view.dart';
import '../../modules/strategy/bindings/strategy_binding.dart';
import '../../modules/strategy/views/okrs_view.dart';
import '../../modules/strategy/views/project_funding_view.dart';
import '../../modules/strategy/views/project_roadmap_view.dart';
import '../../modules/strategy/views/strategy_view.dart';
import '../../modules/strategy/views/template_library_view.dart';
import '../../modules/strategy/views/twelve_week_year_view.dart';
import '../../modules/tasks/bindings/tasks_binding.dart';
import '../../modules/tasks/views/tasks_view.dart';
import '../../modules/vault/bindings/vault_binding.dart';
import '../../modules/vault/views/vault_view.dart';
import '../../modules/workflows/bindings/workflows_binding.dart';
import '../../modules/workflows/views/workflows_view.dart';
import '../../modules/workspace_runtime/bindings/workspace_runtime_binding.dart';
import '../../modules/workspace_runtime/views/blocked_work_view.dart';
import '../../modules/workspace_runtime/views/needs_you_view.dart';
import '../../modules/workspace_runtime/views/work_inspector_view.dart';

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

/// Ánh xạ TẠM THỜI giữa index cũ trong `DashboardNavConfig` và module canonical
/// mới — chỉ tồn tại trong giai đoạn chuyển tiếp (Task 9). Các index KHÔNG có
/// mặt ở đây (OKRs, 12WY, roadmap, template library, project funding,
/// needs-you, blocked-work, work-inspector, organization, skill registry)
/// vẫn hiển thị tại chỗ qua `DashboardContentBody` — chưa có route riêng,
/// đúng tinh thần "retain feature pages initially" của Task 9.
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

/// Route thật cho từng module (trừ `hub` — hub dùng route `/hub` sẵn có,
/// lắp ráp trực tiếp trong `app_pages.dart` vì nó còn phải host
/// `DashboardContentBody` cho các mục sidebar chưa migrate).
///
/// Mỗi route bọc view HIỆN CÓ (không sửa nội dung/visual) bằng `AppShell`
/// (sidebar/topbar/floating voice/banner) — đúng nguyên tắc Task 9: chỉ
/// chuyển quyền sở hữu chrome, không viết lại widget nghiệp vụ.
final List<GetPage> moduleRoutes = [
  GetPage(
    name: WorkspaceModule.tasks.path,
    page: () => const AppShell(activeModule: WorkspaceModule.tasks, child: TasksView()),
    binding: TasksBinding(),
    middlewares: [AuthMiddleware(), ProjectSetupGuardMiddleware()],
  ),
  GetPage(
    name: WorkspaceModule.approvals.path,
    page: () => const AppShell(activeModule: WorkspaceModule.approvals, child: ApprovalsView()),
    binding: ApprovalsBinding(),
    middlewares: [AuthMiddleware(), ProjectSetupGuardMiddleware()],
  ),
  GetPage(
    name: WorkspaceModule.strategy.path,
    page: () => const AppShell(activeModule: WorkspaceModule.strategy, child: StrategyView()),
    binding: StrategyBinding(),
    middlewares: [AuthMiddleware(), ProjectSetupGuardMiddleware()],
  ),
  GetPage(
    name: WorkspaceModule.agents.path,
    page: () => const AppShell(activeModule: WorkspaceModule.agents, child: AgentsView()),
    binding: AgentsBinding(),
    middlewares: [AuthMiddleware(), ProjectSetupGuardMiddleware()],
  ),
  GetPage(
    name: WorkspaceModule.vault.path,
    page: () => AppShell(
      activeModule: WorkspaceModule.vault,
      child: CapabilityGatedView.gated(
        moduleName: 'Vault & Knowledge Store',
        capabilitySelector: (m) => m.vaultSupported,
        child: const VaultView(),
      ),
    ),
    binding: VaultBinding(),
    middlewares: [AuthMiddleware(), ProjectSetupGuardMiddleware()],
  ),
  GetPage(
    name: WorkspaceModule.sales.path,
    page: () => AppShell(
      activeModule: WorkspaceModule.sales,
      child: CapabilityGatedView.gated(
        moduleName: 'Sales CRM & Deals',
        capabilitySelector: (m) => m.salesSupported,
        child: const SalesView(),
      ),
    ),
    binding: SalesBinding(),
    middlewares: [AuthMiddleware(), ProjectSetupGuardMiddleware()],
  ),
  GetPage(
    name: WorkspaceModule.marketing.path,
    page: () => AppShell(
      activeModule: WorkspaceModule.marketing,
      child: CapabilityGatedView.gated(
        moduleName: 'Marketing Cockpit',
        capabilitySelector: (m) => m.marketingSupported,
        child: const MarketingCockpitView(),
      ),
    ),
    binding: MarketingBinding(),
    middlewares: [AuthMiddleware(), ProjectSetupGuardMiddleware()],
  ),
  GetPage(
    name: WorkspaceModule.finance.path,
    page: () => const AppShell(activeModule: WorkspaceModule.finance, child: FinanceView()),
    binding: FinanceBinding(),
    middlewares: [AuthMiddleware(), ProjectSetupGuardMiddleware()],
  ),
  GetPage(
    name: WorkspaceModule.legal.path,
    page: () => const AppShell(activeModule: WorkspaceModule.legal, child: LegalView()),
    binding: LegalBinding(),
    middlewares: [AuthMiddleware(), ProjectSetupGuardMiddleware()],
  ),
  GetPage(
    name: WorkspaceModule.workflows.path,
    page: () => AppShell(
      activeModule: WorkspaceModule.workflows,
      child: CapabilityGatedView.gated(
        moduleName: 'Automated Workflows',
        capabilitySelector: (m) => m.workflowsSupported,
        child: const WorkflowsView(),
      ),
    ),
    binding: WorkflowsBinding(),
    middlewares: [AuthMiddleware(), ProjectSetupGuardMiddleware()],
  ),
  GetPage(
    name: WorkspaceModule.settings.path,
    page: () => const AppShell(activeModule: WorkspaceModule.settings, child: SettingsView()),
    binding: SettingsBinding(),
    middlewares: [AuthMiddleware(), ProjectSetupGuardMiddleware()],
  ),
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
];

/// Test helper (Task 9 Step 1) — tra route đã đăng ký theo path, dùng để
/// assert mỗi module có ĐÚNG MỘT route canonical được guard.
List<GetPage> routesFor(String path) => moduleRoutes.where((route) => route.name == path).toList();
