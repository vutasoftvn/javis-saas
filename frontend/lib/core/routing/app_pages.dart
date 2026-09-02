import 'package:flutter/widgets.dart';
import 'package:get/get.dart';
import 'app_routes.dart';
import 'auth_middleware.dart';
import 'module_routes.dart';

import '../../modules/auth/views/login_view.dart';
import '../../modules/auth/views/register_view.dart';
import '../../modules/auth/bindings/auth_binding.dart';
import '../../modules/dashboard/views/dashboard_view.dart';
import '../../modules/dashboard/bindings/dashboard_binding.dart';
import '../../modules/mission_control/views/mission_control_view.dart';
import '../../modules/mission_control/bindings/mission_control_binding.dart';
import '../../modules/profile/views/profile_view.dart';
import '../../modules/profile/bindings/profile_binding.dart';
import '../../modules/workspace_picker/views/workspace_picker_view.dart';
import '../../modules/workspace_picker/bindings/workspace_picker_binding.dart';
import '../../modules/chat/views/chat_view.dart';
import '../../modules/chat/bindings/chat_binding.dart';

/// Task 9 — `/dashboard` và `/hub` từng trỏ tới 2 view KHÁC NHAU
/// (`DashboardView` so với `HologramHubView`), trùng lặp vai trò "hub". Nay
/// `/hub` là route canonical DUY NHẤT host `DashboardView` (chrome
/// `AppShell` + `DashboardContentBody` cho các mục sidebar chưa migrate);
/// `/dashboard` chỉ còn là alias redirect sang `/hub`.
class AppPages {
  static const initial = AppRoutes.login;

  static final routes = [
    GetPage(
      name: AppRoutes.chat,
      page: () => const ChatView(),
      binding: ChatBinding(),
      middlewares: [AuthMiddleware()],
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
      page: () => const DashboardView(),
      binding: DashboardBinding(),
      middlewares: [AuthMiddleware()],
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
