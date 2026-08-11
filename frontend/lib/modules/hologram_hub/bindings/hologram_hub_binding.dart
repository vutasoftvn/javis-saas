import 'package:get/get.dart';
import '../controllers/hologram_hub_controller.dart';
import '../../dashboard/controllers/dashboard_controller.dart';
import '../../chat/controllers/chat_controller.dart';

class HologramHubBinding extends Bindings {
  @override
  void dependencies() {
    Get.lazyPut<HologramHubController>(() => HologramHubController());
    if (!Get.isRegistered<DashboardController>()) {
      Get.lazyPut<DashboardController>(() => DashboardController());
    }
    if (!Get.isRegistered<ChatController>()) {
      Get.lazyPut<ChatController>(() => ChatController());
    }
  }
}
