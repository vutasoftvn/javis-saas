// COSA Automation MVP — GetX binding (Task 7 / 8).

import 'package:get/get.dart';

import '../controllers/automation_library_controller.dart';
import '../controllers/automation_run_inspector_controller.dart';
import '../services/automation_service.dart';

class AutomationBinding extends Bindings {
  @override
  void dependencies() {
    Get.lazyPut<AutomationService>(() => AutomationService());
    Get.lazyPut<AutomationLibraryController>(
      () => AutomationLibraryController(service: Get.find<AutomationService>()),
    );
    Get.lazyPut<AutomationRunInspectorController>(
      () => AutomationRunInspectorController(service: Get.find<AutomationService>()),
    );
  }
}
