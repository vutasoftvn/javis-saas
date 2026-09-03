import 'package:flutter_test/flutter_test.dart';
import 'package:get/get.dart';
import 'package:frontend/data/models/task_kanban_model.dart';
import 'package:frontend/modules/tasks/controllers/tasks_controller.dart';
import 'package:frontend/modules/tasks/controllers/work_overview_controller.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() {
    Get.reset();
    Get.testMode = true;
  });

  test('todayTasks includes overdue and due-today, non-done tasks only', () {
    final tasksController = TasksController();
    final now = DateTime.now();
    final today = DateTime(now.year, now.month, now.day).toIso8601String();
    final yesterday = DateTime(now.year, now.month, now.day - 1).toIso8601String();
    final tomorrow = DateTime(now.year, now.month, now.day + 1).toIso8601String();

    tasksController.tasks.assignAll([
      TaskKanbanModel(id: '1', title: 'Overdue', status: TaskKanbanStatus.todo, dueDate: yesterday),
      TaskKanbanModel(id: '2', title: 'Due today', status: TaskKanbanStatus.inProgress, dueDate: today),
      TaskKanbanModel(id: '3', title: 'Due tomorrow', status: TaskKanbanStatus.todo, dueDate: tomorrow),
      TaskKanbanModel(id: '4', title: 'Overdue but done', status: TaskKanbanStatus.done, dueDate: yesterday),
      TaskKanbanModel(id: '5', title: 'No due date', status: TaskKanbanStatus.todo, dueDate: null),
    ]);

    final controller = WorkOverviewController(tasksController: tasksController);

    expect(controller.todayTasks.map((t) => t.id).toList(), ['1', '2']);
  });

  test('statusCounts tallies every task by status', () {
    final tasksController = TasksController();
    tasksController.tasks.assignAll([
      TaskKanbanModel(id: '1', title: 'A', status: TaskKanbanStatus.todo),
      TaskKanbanModel(id: '2', title: 'B', status: TaskKanbanStatus.todo),
      TaskKanbanModel(id: '3', title: 'C', status: TaskKanbanStatus.done),
    ]);

    final controller = WorkOverviewController(tasksController: tasksController);

    expect(controller.statusCounts[TaskKanbanStatus.todo], 2);
    expect(controller.statusCounts[TaskKanbanStatus.done], 1);
    expect(controller.statusCounts[TaskKanbanStatus.blocked] ?? 0, 0);
  });
}
