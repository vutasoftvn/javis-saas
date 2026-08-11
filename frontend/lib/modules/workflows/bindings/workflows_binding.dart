import 'package:get/get.dart';
import '../controllers/workflows_controller.dart';

class WorkflowsBinding extends Bindings {
  @override
  void dependencies() {
    Get.lazyPut<WorkflowsController>(
      () => WorkflowsController(),
    );
  }
}
