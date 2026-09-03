import 'package:flutter/widgets.dart';
import 'package:get/get.dart';

import '../../modules/hologram_hub/controllers/founder_command_center_controller.dart';
import 'app_routes.dart';

/// Fast path đồng bộ: khi state `FounderCommandCenterController` đã sẵn và
/// `needsProjectSetup`, đẩy sang `/projects/new` ngay tại tầng routing.
/// Fix race (2026-09-03, Task 5) — path đồng bộ CHỈ fire khi state đã biết,
/// tức `loadDashboardData()` đã chạy xong ít nhất một lần
/// (`projectsLoadedOnce == true`). Trước đó `projectsList` rỗng + `projectsError`
/// null trông giống "0 project" dù thực chất đang tải (rõ nhất ngay sau khi
/// chuyển workspace). Cửa sổ pre-load đó do backstop async
/// `_enforceZeroProjectRedirect()` ở cuối `loadDashboardData()` xử lý — xem
/// `FounderCommandCenterController`.
class ProjectSetupGuardMiddleware extends GetMiddleware {
  @override
  int? get priority => 5;

  @override
  RouteSettings? redirect(String? route) {
    if (route == AppRoutes.projectsNew) return null;
    if (!Get.isRegistered<FounderCommandCenterController>()) return null;
    final fcc = Get.find<FounderCommandCenterController>();
    if (!fcc.projectsLoadedOnce.value) return null;
    if (fcc.needsProjectSetup) {
      return const RouteSettings(name: AppRoutes.projectsNew);
    }
    return null;
  }
}
