import 'package:get/get.dart';
import '../../../data/models/task_kanban_model.dart';
import 'tasks_controller.dart';

/// Đọc lại `TasksController.tasks` đã tải sẵn (không fetch riêng) để tổng
/// hợp 2 khối "Việc hôm nay" và "Thống kê task theo trạng thái" cho tab
/// Tổng quan. Task 3-4 sẽ mở rộng thêm phần project/OKR/12WY cùng file này.
class WorkOverviewController extends GetxController {
  WorkOverviewController({required this.tasksController});

  final TasksController tasksController;

  /// Các task chưa xong (không tính done/cancelled) đã quá hạn hoặc đến hạn
  /// hôm nay, sắp theo hạn tăng dần.
  List<TaskKanbanModel> get todayTasks {
    final now = DateTime.now();
    final startOfToday = DateTime(now.year, now.month, now.day);
    final endOfToday = startOfToday.add(const Duration(days: 1));

    final result = tasksController.tasks.where((t) {
      if (t.status == TaskKanbanStatus.done ||
          t.status == TaskKanbanStatus.cancelled) {
        return false;
      }
      final due = t.dueDate != null ? DateTime.tryParse(t.dueDate!) : null;
      if (due == null) return false;
      return due.isBefore(endOfToday);
    }).toList();

    result.sort((a, b) {
      final dueA = DateTime.tryParse(a.dueDate!)!;
      final dueB = DateTime.tryParse(b.dueDate!)!;
      return dueA.compareTo(dueB);
    });
    return result;
  }

  /// Đếm số task theo từng trạng thái, luôn có đủ tất cả status (mặc định 0).
  Map<TaskKanbanStatus, int> get statusCounts {
    final counts = <TaskKanbanStatus, int>{};
    for (final status in TaskKanbanStatus.values) {
      counts[status] = 0;
    }
    for (final task in tasksController.tasks) {
      counts[task.status] = (counts[task.status] ?? 0) + 1;
    }
    return counts;
  }
}
