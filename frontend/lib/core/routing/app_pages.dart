import 'package:get/get.dart';
import 'app_routes.dart';
import 'auth_middleware.dart';

import '../../modules/auth/views/login_view.dart';
import '../../modules/auth/views/register_view.dart';
import '../../modules/auth/bindings/auth_binding.dart';
import '../../modules/dashboard/views/dashboard_view.dart';
import '../../modules/dashboard/bindings/dashboard_binding.dart';
import '../../modules/hologram_hub/views/hologram_hub_view.dart';
import '../../modules/hologram_hub/bindings/hologram_hub_binding.dart';
import '../../modules/mission_control/views/mission_control_view.dart';
import '../../modules/mission_control/bindings/mission_control_binding.dart';

class AppPages {
  static const initial = AppRoutes.login;

  static final routes = [
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
      name: AppRoutes.dashboard,
      page: () => const DashboardView(),
      binding: DashboardBinding(),
      middlewares: [AuthMiddleware()],
    ),
    GetPage(
      name: AppRoutes.hub,
      page: () => const HologramHubView(),
      binding: HologramHubBinding(),
      middlewares: [AuthMiddleware()],
    ),
    GetPage(
      name: AppRoutes.missionControl,
      page: () => const MissionControlView(),
      binding: MissionControlBinding(),
      middlewares: [AuthMiddleware()],
    ),
  ];
}



