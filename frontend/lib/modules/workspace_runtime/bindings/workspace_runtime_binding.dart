import 'package:get/get.dart';
import '../controllers/workspace_runtime_controller.dart';

class WorkspaceRuntimeBinding extends Bindings {
  @override
  void dependencies() {
    Get.lazyPut<WorkspaceRuntimeController>(() => WorkspaceRuntimeController());
  }
}
