import 'package:get/get.dart';
import '../../../data/models/task_kanban_model.dart';
import '../../../data/models/project_operating_setup_model.dart';
import '../../strategy/services/okr_service.dart';
import '../../strategy/services/project_operating_setup_service.dart';
import '../../strategy/services/twelve_wy_service.dart';
import 'tasks_controller.dart';

/// Đọc lại `TasksController.tasks` đã tải sẵn (không fetch riêng) để tổng
/// hợp 2 khối "Việc hôm nay" và "Thống kê task theo trạng thái" cho tab
/// Tổng quan. Task 3 mở rộng thêm phần chọn project + thông tin quản trị
/// project (`ProjectOperatingSetup`). Task 4 mở rộng thêm khối OKR/12WY
/// rút gọn.
class WorkOverviewController extends GetxController {
  WorkOverviewController({
    required this.tasksController,
    ProjectOperatingSetupService? projectOperatingSetupService,
    OkrService? okrService,
    TwelveWyService? twelveWyService,
  })  : _projectOperatingSetupService =
            projectOperatingSetupService ?? ProjectOperatingSetupService(),
        _okrService = okrService ?? OkrService(),
        _twelveWyService = twelveWyService ?? TwelveWyService();

  final TasksController tasksController;
  final ProjectOperatingSetupService _projectOperatingSetupService;
  final OkrService _okrService;
  final TwelveWyService _twelveWyService;

  /// Tỉ lệ hoàn thành trung bình các Key Result (0.0-1.0), null khi chưa tải
  /// hoặc không có key result nào.
  final okrCompletionRatio = RxnDouble();

  /// Điểm thực thi tuần hiện tại của chu kỳ 12WY, null khi chưa tải hoặc
  /// chưa có chu kỳ active.
  final twelveWyExecutionScore = RxnDouble();
  final isOkrSummaryLoading = false.obs;
  final okrSummaryError = RxnString();

  /// Project đang được chọn trong dropdown "Thông tin quản trị project".
  final selectedProjectId = RxnString();

  /// Kết quả `ProjectOperatingSetupService.get()` cho project đang chọn.
  final projectSetup = Rxn<ProjectOperatingSetup>();
  final isProjectInfoLoading = false.obs;
  final projectInfoError = RxnString();

  /// Chọn 1 project và tải thông tin quản trị (operating setup) tương ứng.
  ///
  /// Guard theo `selectedProjectId.value != projectId` sau mỗi `await`: nếu
  /// Founder đổi project A → B nhanh và response của A (chậm) về SAU response
  /// của B, response cũ (A) không được phép ghi đè state của B — chỉ request
  /// khớp với project đang chọn tại thời điểm HIỆN TẠI mới được áp dụng.
  Future<void> selectProject(String projectId) async {
    selectedProjectId.value = projectId;
    isProjectInfoLoading.value = true;
    projectInfoError.value = null;
    try {
      final setup = await _projectOperatingSetupService.get(projectId);
      if (selectedProjectId.value != projectId) return;
      projectSetup.value = setup;
    } catch (e) {
      if (selectedProjectId.value != projectId) return;
      projectInfoError.value = e.toString();
    } finally {
      if (selectedProjectId.value == projectId) {
        isProjectInfoLoading.value = false;
      }
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

  /// Tính tỉ lệ hoàn thành OKR trung bình từ các key result (current/target,
  /// clamp 0-1) và đọc điểm thực thi tuần 12WY của project đang chọn.
  Future<void> loadOkrAndTwelveWySummary() async {
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

      final dashboard = await _twelveWyService.getDashboard(selectedProjectId.value);
      twelveWyExecutionScore.value = dashboard?.currentWeekExecutionScore;
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
