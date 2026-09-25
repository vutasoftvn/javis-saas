import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/data/models/task_kanban_model.dart';
import 'package:frontend/modules/tasks/controllers/tasks_controller.dart';
import 'package:frontend/modules/tasks/services/task_service.dart';
import 'package:get/get.dart';

class _FakeTaskService extends TaskService {
  final created = <Map<String, Object?>>[];
  final statusUpdates = <String>[];

  @override
  Future<List<TaskKanbanModel>> getTasksList() async => const [];

  @override
  Future<TaskKanbanModel> createTypedTask(
    String title, {
    TaskKanbanStatus status = TaskKanbanStatus.todo,
    String? priority = 'medium',
    String? dueAt,
    dynamic assigneeMemberId,
    String? executionMode,
    String? function,
    String? projectId,
    String? weeklyCommitmentId,
    String? idempotencyKey,
  }) async {
    created.add({'title': title, 'projectId': projectId});
    // Backend luôn tạo task ở `todo`.
    return TaskKanbanModel(id: 'task-1', title: title, projectId: projectId);
  }

  @override
  Future<TaskKanbanModel> updateTaskStatus(String taskId, String status) async {
    statusUpdates.add(status);
    return TaskKanbanModel(
      id: taskId,
      title: 'x',
      status: TaskKanbanStatus.fromString(status),
    );
  }
}

// POST /operations/tasks bắt buộc projectId và không nhận status: thêm task
// từ cột "Đang làm" phải gửi project và chuyển trạng thái sau khi tạo.
void main() {
  setUp(Get.reset);

  test('addTask sends the project and moves the task to the requested column', () async {
    final service = _FakeTaskService();
    final controller = TasksController(taskService: service);

    await controller.addTask('Viết landing page', 'in_progress', projectId: 'proj-7');

    expect(service.created.single['projectId'], 'proj-7');
    expect(service.statusUpdates, ['in_progress']);
    expect(controller.tasks.single.status, TaskKanbanStatus.inProgress);
  });

  test('addTask in the todo column does not issue an extra status update', () async {
    final service = _FakeTaskService();
    final controller = TasksController(taskService: service);

    await controller.addTask('Gọi khách hàng', 'todo', projectId: 'proj-7');

    expect(service.statusUpdates, isEmpty);
  });
}
