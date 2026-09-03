import 'package:get/get.dart';
import '../../../data/models/task_kanban_model.dart';
import '../../../data/models/project_operating_setup_model.dart';
import '../../strategy/services/project_operating_setup_service.dart';
import 'tasks_controller.dart';

/// Đọc lại `TasksController.tasks` đã tải sẵn (không fetch riêng) để tổng
/// hợp 2 khối "Việc hôm nay" và "Thống kê task theo trạng thái" cho tab
/// Tổng quan. Task 3 mở rộng thêm phần chọn project + thông tin quản trị
/// project (`ProjectOperatingSetup`). Task 4 sẽ mở rộng thêm OKR/12WY.
class WorkOverviewController extends GetxController {
  WorkOverviewController({
    required this.tasksController,
    ProjectOperatingSetupService? projectOperatingSetupService,
  }) : _projectOperatingSetupService =
           projectOperatingSetupService ?? ProjectOperatingSetupService();

  final TasksController tasksController;
  final ProjectOperatingSetupService _projectOperatingSetupService;

  /// Project đang được chọn trong dropdown "Thông tin quản trị project".
  final selectedProjectId = RxnString();

  /// Kết quả `ProjectOperatingSetupService.get()` cho project đang chọn.
  final projectSetup = Rxn<ProjectOperatingSetup>();
  final isProjectInfoLoading = false.obs;
  final projectInfoError = RxnString();

  /// Chọn 1 project và tải thông tin quản trị (operating setup) tương ứng.
  Future<void> selectProject(String projectId) async {
    selectedProjectId.value = projectId;
    isProjectInfoLoading.value = true;
    projectInfoError.value = null;
    try {
      projectSetup.value = await _projectOperatingSetupService.get(projectId);
    } catch (e) {
      projectInfoError.value = e.toString();
    } finally {
      isProjectInfoLoading.value = false;
    }
  }

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
