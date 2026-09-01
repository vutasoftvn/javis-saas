import 'package:get/get.dart';
import '../../../core/widgets/app_toast.dart';
import '../../../data/models/task_kanban_model.dart';
import '../../../modules/tasks/services/task_service.dart';

class TasksController extends GetxController {
  final TaskService _taskService = TaskService();

  final isLoading = false.obs;
  final tasks = <TaskKanbanModel>[].obs;
  final activeFilter = 'all'.obs; // 'all', 'active', 'approval_blocked', 'completed'

  @override
  void onInit() {
    super.onInit();
    loadTasks();
  }

  Future<void> loadTasks() async {
    isLoading.value = true;
    try {
      final list = await _taskService.getTasksList();
      tasks.value = list;
    } finally {
      isLoading.value = false;
    }
  }

  Future<void> addTask(String title, String statusStr) async {
    if (title.trim().isEmpty) return;

    final targetStatus = TaskKanbanStatus.fromString(statusStr);
    final tempTask = TaskKanbanModel(
      id: 'temp_${DateTime.now().millisecondsSinceEpoch}',
      title: title.trim(),
      status: targetStatus,
      createdAt: DateTime.now(),
    );

    // Optimistic UI update
    tasks.insert(0, tempTask);

    try {
      final result = await _taskService.createTypedTask(title.trim(), status: targetStatus);
      final index = tasks.indexWhere((t) => t.id == tempTask.id);
      if (index != -1) {
        tasks[index] = result;
      }
    } catch (e) {
      tasks.removeWhere((t) => t.id == tempTask.id);
      AppToast.error('Không thể tạo công việc');
    }
  }

  Future<void> moveTask(String taskId, String newStatusStr) async {
    final index = tasks.indexWhere((t) => t.id == taskId);
    if (index == -1) return;

    final oldStatus = tasks[index].status;
    final newStatus = TaskKanbanStatus.fromString(newStatusStr);
    if (oldStatus == newStatus) return;

    // Optimistic UI update
    tasks[index] = tasks[index].copyWith(status: newStatus);
    tasks.refresh();

    try {
      await _taskService.updateTaskStatus(taskId, newStatus.value);
    } catch (e) {
      // Revert on failure
      tasks[index] = tasks[index].copyWith(status: oldStatus);
      tasks.refresh();
      AppToast.error('Không thể cập nhật trạng thái');
    }
  }


  Future<void> pauseTask(String taskId) async {
    await moveTask(taskId, 'blocked');
  }

  Future<void> resumeTask(String taskId) async {
    await moveTask(taskId, 'in_progress');
  }

  Future<void> approveTask(String taskId) async {
    await moveTask(taskId, 'in_progress');
  }

  Future<void> cancelTask(String taskId) async {
    await moveTask(taskId, 'cancelled');
  }
}
