import 'package:get/get.dart';
import '../../../data/models/task_kanban_model.dart';
import '../../strategy/services/okr_service.dart';
import 'tasks_controller.dart';

/// Đọc lại `TasksController.tasks` đã tải sẵn (không fetch riêng) để tổng
/// hợp 2 khối "Việc hôm nay" và "Thống kê task theo trạng thái" cho tab
/// Tổng quan, kèm khối OKR rút gọn (tỉ lệ hoàn thành key result).
class WorkOverviewController extends GetxController {
  WorkOverviewController({
    required this.tasksController,
    OkrService? okrService,
  }) : _okrService = okrService ?? OkrService();

  final TasksController tasksController;
  final OkrService _okrService;

  /// Tỉ lệ hoàn thành trung bình các Key Result (0.0-1.0), null khi chưa tải
  /// hoặc không có key result nào.
  final okrCompletionRatio = RxnDouble();
  final isOkrSummaryLoading = false.obs;
  final okrSummaryError = RxnString();

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

  /// Tính tỉ lệ hoàn thành OKR trung bình từ các key result (current/target,
  /// clamp 0-1).
  Future<void> loadOkrSummary() async {
    isOkrSummaryLoading.value = true;
    okrSummaryError.value = null;
    try {
      final krResult = await _okrService.getKeyResults();
      if (!krResult.isFailure && krResult.items.isNotEmpty) {
        final ratios = krResult.items.map((kr) {
          final current = (kr['current_value'] as num?)?.toDouble() ?? 0.0;
          final target = (kr['target_value'] as num?)?.toDouble() ?? 0.0;
          if (target <= 0) return 0.0;
          return (current / target).clamp(0.0, 1.0);
        });
        okrCompletionRatio.value = ratios.reduce((a, b) => a + b) / ratios.length;
      }
    } catch (e) {
      okrSummaryError.value = e.toString();
    } finally {
      isOkrSummaryLoading.value = false;
    }
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
