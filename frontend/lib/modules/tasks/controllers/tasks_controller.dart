import 'package:get/get.dart';
import '../../../data/services/task_service.dart';

class TasksController extends GetxController {
  final TaskService _taskService = TaskService();

  final isLoading = false.obs;
  final tasks = <Map<String, dynamic>>[].obs;
  final activeFilter = 'all'.obs; // 'all', 'active', 'approval_blocked', 'completed'

  @override
  void onInit() {
    super.onInit();
    loadTasks();
  }

  Future<void> loadTasks() async {
    isLoading.value = true;
    final res = await _taskService.getTasks();
    tasks.value = List<Map<String, dynamic>>.from(res.map((t) => Map<String, dynamic>.from(t)));
    isLoading.value = false;
  }

  Future<void> addTask(String title, String status) async {
    if (title.isEmpty) return;

    // Optimistic UI update
    final tempTask = {
      'id': 'temp_${DateTime.now().millisecondsSinceEpoch}',
      'title': title,
      'status': status,
      'created_at': DateTime.now().toIso8601String(),
    };
    tasks.insert(0, tempTask);

    final result = await _taskService.createTask(title, status: status);
    if (result != null) {
      final index = tasks.indexWhere((t) => t['id'] == tempTask['id']);
      if (index != -1) {
        tasks[index] = Map<String, dynamic>.from(result);
      }
    } else {
      tasks.removeWhere((t) => t['id'] == tempTask['id']);
      Get.snackbar('Error', 'Failed to create task');
    }
  }

  Future<void> moveTask(String taskId, String newStatus) async {
    final index = tasks.indexWhere((t) => t['id'] == taskId);
    if (index == -1) return;

    final oldStatus = tasks[index]['status'];
    if (oldStatus == newStatus) return;

    // Optimistic UI update
    tasks[index] = {...tasks[index], 'status': newStatus};
    tasks.refresh();

    final result = await _taskService.updateTaskStatus(taskId, newStatus);
    if (result == null) {
      // Revert on failure
      tasks[index] = {...tasks[index], 'status': oldStatus};
      tasks.refresh();
      Get.snackbar('Error', 'Failed to move task');
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

