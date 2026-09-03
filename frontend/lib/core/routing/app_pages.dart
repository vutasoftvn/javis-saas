import 'package:flutter/widgets.dart';
import 'package:get/get.dart';
import 'app_routes.dart';
import 'auth_middleware.dart';
import 'module_routes.dart';
import 'project_setup_guard_middleware.dart';

import '../../modules/auth/views/login_view.dart';
import '../../modules/auth/views/register_view.dart';
import '../../modules/auth/bindings/auth_binding.dart';
import '../../modules/hologram_hub/views/hologram_hub_view.dart';
import '../../modules/mission_control/views/mission_control_view.dart';
import '../../modules/mission_control/bindings/mission_control_binding.dart';
import '../../modules/profile/views/profile_view.dart';
import '../../modules/profile/bindings/profile_binding.dart';
import '../../modules/workspace_picker/views/workspace_picker_view.dart';
import '../../modules/workspace_picker/bindings/workspace_picker_binding.dart';
import '../../modules/strategy/views/project_setup_view.dart';
import '../../modules/strategy/controllers/project_setup_controller.dart';
import '../../modules/hologram_hub/controllers/founder_command_center_controller.dart';
import '../shell/app_shell_controller.dart';

/// Task 9-6 — `/dashboard` và `/hub` từng trỏ tới 2 view khác (lặp vai trò).
/// Nay `/hub` render `HologramHubView` trực tiếp (không `AppShell`/sidebar);
/// `/dashboard` là alias redirect sang `/hub`.
class AppPages {
  static const initial = AppRoutes.login;

  static final routes = [
    // Task 10 — quyết định đã duyệt (2026-09-02, Option 1): Hub sở hữu một
    // dockable chat panel + một phiên hội thoại dùng chung; `/chat` không
    // còn tự render `ChatView` nữa mà LUÔN redirect sang `/hub?panel=chat`.
    // `LegacyModuleRedirectMiddleware` chấp nhận bất kỳ path nào (kể cả có
    // query string) làm `canonicalPath` — GetX tự parse query string đó qua
    // `Get.routeTree.matchRoute` ngay trong vòng lặp redirect
    // (`route_middleware.dart: needRecheck()`), nạp vào `Get.parameters`
    // đúng như `Get.toNamed` thông thường — không cần middleware/cơ chế
    // riêng nào khác. `ChatView`/`ChatBinding` vẫn giữ nguyên trong
    // `modules/chat/` (không xoá) nhưng không còn được route tới trực tiếp.
    GetPage(
      name: AppRoutes.chat,
      page: () => const SizedBox.shrink(),
      middlewares: [LegacyModuleRedirectMiddleware('${AppRoutes.hub}?panel=chat')],
    ),
    GetPage(
      name: AppRoutes.login,
      page: () => const LoginView(),
      binding: AuthBinding(),
    ),
    GetPage(
      name: AppRoutes.register,
      page: () => const RegisterView(),
      binding: AuthBinding(),
    ),
    GetPage(
      name: AppRoutes.projectsNew,
      page: () => const ProjectSetupView(),
      binding: BindingsBuilder(() {
        // FCC do shell sở hữu; route này có thể vào thẳng qua guard trước khi
        // AppShell mount, nên tự đảm bảo nó tồn tại.
        AppShellController.ensureShellDependencies();
        // Guard redirect từ `/hub` bằng `offAllNamed`: FCC non-permanent của
        // `DashboardBinding` vẫn còn sống lúc binding này chạy nên
        // `ensureShellDependencies()` (guard `isRegistered`) KHÔNG nâng cấp nó;
        // ngay sau đó `/hub` bị pop -> instance đó bị dispose -> `/projects/new`
        // mất FCC. Ép instance hiện có (hoặc tạo mới) thành permanent.
        final fcc = Get.isRegistered<FounderCommandCenterController>()
            ? Get.find<FounderCommandCenterController>()
            : FounderCommandCenterController();
        Get.put<FounderCommandCenterController>(fcc, permanent: true);
        Get.lazyPut<ProjectSetupController>(() => ProjectSetupController());
      }),
      middlewares: [AuthMiddleware()],
    ),
    GetPage(
      name: AppRoutes.workspacePicker,
      page: () => const WorkspacePickerView(),
      binding: WorkspacePickerBinding(),
      // Task 4 — AuthMiddleware (đã đăng nhập local) + guard riêng cho
      // đúng route argument (platformToken + workspaces) — trước đây route
      // này không có middleware nào, cho phép render picker "chết" nếu vào
      // thẳng bằng deep-link/hot-restart mất arguments.
      middlewares: [AuthMiddleware(), WorkspacePickerGuardMiddleware()],
    ),
    // Task 9 — `/dashboard` không còn tự render: chỉ redirect sang `/hub`
    // (route canonical mới), giữ lại để không phá deep-link/bookmark cũ.
    GetPage(
      name: AppRoutes.dashboard,
      page: () => const SizedBox.shrink(),
      middlewares: [LegacyModuleRedirectMiddleware(AppRoutes.hub)],
    ),
    GetPage(
      name: AppRoutes.hub,
      page: () => const HologramHubView(),
      binding: BindingsBuilder(() {
        AppShellController.ensureShellDependencies();
      }),
      middlewares: [AuthMiddleware(), ProjectSetupGuardMiddleware()],
    ),
    GetPage(
      name: AppRoutes.missionControl,
      page: () => const MissionControlView(),
      binding: MissionControlBinding(),
      middlewares: [AuthMiddleware()],
    ),
    GetPage(
      name: AppRoutes.profile,
      page: () => const ProfileView(),
      binding: ProfileBinding(),
      middlewares: [AuthMiddleware()],
    ),

    // Task 9 — 10 route flat cũ bên dưới (approvals/agents/tasks/vault/
    // strategy/sales/marketing/finance/legal/workflows) KHÔNG còn tự render
    // nữa — mỗi module giờ có route canonical thật dưới `/work/*`
    // (`moduleRoutes`, xem cuối danh sách). Route cũ chỉ redirect, giữ lại
    // để không phá deep-link/bookmark cũ (per Task 9 brief: "retain legacy
    // URLs").
    GetPage(
      name: AppRoutes.approvals,
      page: () => const SizedBox.shrink(),
      middlewares: [LegacyModuleRedirectMiddleware(WorkspaceModule.approvals.path)],
    ),
    GetPage(
      name: AppRoutes.agents,
      page: () => const SizedBox.shrink(),
      middlewares: [LegacyModuleRedirectMiddleware(WorkspaceModule.agents.path)],
    ),
    GetPage(
      name: AppRoutes.tasks,
      page: () => const SizedBox.shrink(),
      middlewares: [LegacyModuleRedirectMiddleware(WorkspaceModule.tasks.path)],
    ),
    GetPage(
      name: AppRoutes.vault,
      page: () => const SizedBox.shrink(),
      middlewares: [LegacyModuleRedirectMiddleware(WorkspaceModule.vault.path)],
    ),
    GetPage(
      name: AppRoutes.strategy,
      page: () => const SizedBox.shrink(),
      middlewares: [LegacyModuleRedirectMiddleware(WorkspaceModule.strategy.path)],
    ),
    GetPage(
      name: AppRoutes.sales,
      page: () => const SizedBox.shrink(),
      middlewares: [LegacyModuleRedirectMiddleware(WorkspaceModule.sales.path)],
    ),
    GetPage(
      name: AppRoutes.marketing,
      page: () => const SizedBox.shrink(),
      middlewares: [LegacyModuleRedirectMiddleware(WorkspaceModule.marketing.path)],
    ),
    GetPage(
      name: AppRoutes.finance,
      page: () => const SizedBox.shrink(),
      middlewares: [LegacyModuleRedirectMiddleware(WorkspaceModule.finance.path)],
    ),
    GetPage(
      name: AppRoutes.legal,
      page: () => const SizedBox.shrink(),
      middlewares: [LegacyModuleRedirectMiddleware(WorkspaceModule.legal.path)],
    ),
    GetPage(
      name: AppRoutes.workflows,
      page: () => const SizedBox.shrink(),
      middlewares: [LegacyModuleRedirectMiddleware(WorkspaceModule.workflows.path)],
    ),

    // Task 9 — route canonical thật cho mọi module (mỗi route có
    // binding/page/guard riêng, xem `module_routes.dart`). `settings` là
    // route MỚI HOÀN TOÀN — trước đây chỉ vào được qua index sidebar cũ.
    ...moduleRoutes,
  ];
}
