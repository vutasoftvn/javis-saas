import 'package:get/get.dart';
import '../controllers/workspace_picker_controller.dart';

class WorkspacePickerBinding extends Bindings {
  @override
  void dependencies() {
    Get.lazyPut<WorkspacePickerController>(() => WorkspacePickerController());
  }
}
