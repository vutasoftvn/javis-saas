import 'package:get/get.dart';
import '../controllers/ai_operations_controller.dart';
import '../../../data/services/execution_service.dart';

class AiOperationsBinding extends Bindings {
  @override
  void dependencies() {
    Get.lazyPut<ExecutionService>(() => ExecutionService());
    Get.lazyPut<AiOperationsController>(() => AiOperationsController());
  }
}
