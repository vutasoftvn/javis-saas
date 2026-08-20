import 'package:get/get.dart';
import '../controllers/hologram_hub_controller.dart';
import '../controllers/founder_command_center_controller.dart';
import '../../dashboard/controllers/dashboard_controller.dart';

class HologramHubBinding extends Bindings {
  @override
  void dependencies() {
    Get.lazyPut<HologramHubController>(() => HologramHubController());
    Get.lazyPut<FounderCommandCenterController>(() => FounderCommandCenterController());
    if (!Get.isRegistered<DashboardController>()) {
      Get.lazyPut<DashboardController>(() => DashboardController());
    }
  }
}
