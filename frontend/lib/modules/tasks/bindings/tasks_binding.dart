import 'package:get/get.dart';
import '../controllers/tasks_controller.dart';
import '../controllers/work_overview_controller.dart';

class TasksBinding extends Bindings {
  @override
  void dependencies() {
    Get.lazyPut<TasksController>(() => TasksController());
    Get.lazyPut<WorkOverviewController>(
      () => WorkOverviewController(tasksController: Get.find<TasksController>()),
    );
  }
}
