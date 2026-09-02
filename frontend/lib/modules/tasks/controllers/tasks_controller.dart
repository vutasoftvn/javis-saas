import 'package:get/get.dart';
import '../../../core/widgets/app_toast.dart';
import '../../../core/runtime/mutation_gate.dart';
import '../../../data/models/task_kanban_model.dart';
import '../../../modules/tasks/services/task_service.dart';

class TasksController extends GetxController {
  TasksController({MutationGate? mutationGate})
      : _mutationGate = mutationGate ?? SessionMutationGate();

  final TaskService _taskService = TaskService();
  // Task 5 — cùng nguyên tắc với ApprovalsController: gate DUY NHẤT trước
  // khi đổi trạng thái task (kéo-thả Kanban hoặc nút pause/resume/approve/
  // cancel), đọc `SessionController.active.runtime`.
  final MutationGate _mutationGate;

  MutationPermission mutationPermission() => _mutationGate.check(isMutation: true);

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

  /// [confirmed] — bắt buộc `true` khi gate trả [MutationPermission.confirmDegraded]
  /// và người dùng đã xác nhận qua `confirmDegradedMutation` (xem
  /// `kanban_task_card.dart`). Kéo-thả Kanban khi degraded sẽ không tự động
  /// coi là đã xác nhận — item chỉ đứng yên, không mất optimistic state vì
  /// chưa từng đổi.
  Future<void> moveTask(String taskId, String newStatusStr, {bool confirmed = false}) async {
    final permission = mutationPermission();
    // blockedOffline/blockedReadOnly: các nút pause/resume/approve/cancel
    // trong `kanban_task_card.dart` PHẢI đã disable trước khi bấm được — nếu
    // vẫn tới đây (vd. kéo-thả), im lặng không đổi trạng thái, không gọi
    // service, không toast lỗi giả.
    if (permission.isHardBlocked) return;
    if (permission == MutationPermission.confirmDegraded && !confirmed) return;

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


  Future<void> pauseTask(String taskId, {bool confirmed = false}) async {
    await moveTask(taskId, 'blocked', confirmed: confirmed);
  }

  Future<void> resumeTask(String taskId, {bool confirmed = false}) async {
    await moveTask(taskId, 'in_progress', confirmed: confirmed);
  }

  Future<void> approveTask(String taskId, {bool confirmed = false}) async {
    await moveTask(taskId, 'in_progress', confirmed: confirmed);
  }

  Future<void> cancelTask(String taskId, {bool confirmed = false}) async {
    await moveTask(taskId, 'cancelled', confirmed: confirmed);
  }
}
