import 'package:get/get.dart';
import '../controllers/mission_control_controller.dart';
import '../services/mission_control_service.dart';

class MissionControlBinding extends Bindings {
  @override
  void dependencies() {
    Get.lazyPut<MissionControlService>(() => MissionControlService());
    Get.lazyPut<MissionControlController>(
      () => MissionControlController(service: Get.find<MissionControlService>()),
    );
  }
}
