import 'package:get/get.dart';
import '../controllers/settings_controller.dart';
import '../controllers/permissions_controller.dart';
import '../services/permissions_service.dart';

class SettingsBinding extends Bindings {
  @override
  void dependencies() {
    Get.lazyPut<SettingsController>(
      () => SettingsController(),
    );
    Get.lazyPut<PermissionsService>(
      () => PermissionsService(),
    );
    Get.lazyPut<PermissionsController>(
      () => PermissionsController(),
    );
  }
}
