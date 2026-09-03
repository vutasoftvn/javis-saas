import 'package:flutter/widgets.dart';
import 'package:get/get.dart';

import '../../modules/hologram_hub/controllers/founder_command_center_controller.dart';
import 'app_routes.dart';

/// Fast path đồng bộ: khi state `FounderCommandCenterController` đã sẵn và
/// `needsProjectSetup`, đẩy sang `/projects/new` ngay tại tầng routing.
/// Trường hợp state chưa tải xong (điều hướng vào `/hub` trước khi projects
/// về) do backstop async ở cuối `loadDashboardData()` xử lý — xem
/// `FounderCommandCenterController`.
class ProjectSetupGuardMiddleware extends GetMiddleware {
  @override
  int? get priority => 5;

  @override
  RouteSettings? redirect(String? route) {
    if (route == AppRoutes.projectsNew) return null;
    if (!Get.isRegistered<FounderCommandCenterController>()) return null;
    final fcc = Get.find<FounderCommandCenterController>();
    if (fcc.needsProjectSetup) {
      return const RouteSettings(name: AppRoutes.projectsNew);
    }
    return null;
  }
}
