import 'package:get/get.dart';
import '../controllers/strategy_controller.dart';
import '../controllers/foundation_controller.dart';
import '../controllers/project_orchestration_controller.dart';

class StrategyBinding extends Bindings {
  @override
  void dependencies() {
    Get.lazyPut<StrategyController>(() => StrategyController());
    Get.lazyPut<FoundationController>(() => FoundationController());
    Get.lazyPut<ProjectOrchestrationController>(() => ProjectOrchestrationController());
  }
}
