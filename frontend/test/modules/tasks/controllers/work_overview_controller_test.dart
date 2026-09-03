import 'dart:async';

import 'package:flutter_test/flutter_test.dart';
import 'package:get/get.dart';
import 'package:frontend/core/contracts/enums.generated.dart';
import 'package:frontend/data/models/task_kanban_model.dart';
import 'package:frontend/data/models/project_operating_setup_model.dart';
import 'package:frontend/modules/strategy/models/strategy_list_result.dart';
import 'package:frontend/modules/strategy/services/okr_service.dart';
import 'package:frontend/modules/strategy/services/project_operating_setup_service.dart';
import 'package:frontend/modules/strategy/services/twelve_wy_service.dart';
import 'package:frontend/data/models/twelve_wy_model.dart';
import 'package:frontend/modules/tasks/controllers/tasks_controller.dart';
import 'package:frontend/modules/tasks/controllers/work_overview_controller.dart';

class FakeOkrService extends OkrService {
  @override
  Future<StrategyListResult<Map<String, dynamic>>> getKeyResults({String? objectiveId}) async {
    return StrategyListResult.success([
      {'current_value': 50.0, 'target_value': 100.0},
      {'current_value': 100.0, 'target_value': 100.0},
    ]);
  }
}

/// Fake ném lỗi để tái hiện đúng finding 1: `getKeyResults()` fail (vd lỗi
/// secure-storage khi đọc workspace id) không được phép trở thành unhandled
/// async exception — phải bị bắt và phản ánh qua `okrSummaryError`.
class ThrowingOkrService extends OkrService {
  @override
  Future<StrategyListResult<Map<String, dynamic>>> getKeyResults({String? objectiveId}) async {
    throw Exception('secure-storage fail-closed: không đọc được workspace id');
  }
}

class FakeTwelveWyService extends TwelveWyService {
  @override
  Future<TwelveWyDashboardModel?> getDashboard(dynamic projectId) async {
    return TwelveWyDashboardModel(
      cycle: TwelveWeekCycleModel(
        id: 1,
        workspaceId: 1,
        title: 'Cycle 1',
        visionStatement: '',
        stageAtStart: 'P0_DISCOVERY',
        currentWeek: 2,
        totalWeeks: 12,
        overallExecutionScore: 0.75,
        status: 'ACTIVE',
        createdAt: DateTime.now(),
      ),
      currentWeek: 2,
      currentWeekExecutionScore: 0.75,
      tacticsByWeek: const {},
      weeklyScores: const {},
    );
  }
}

class FakeProjectOperatingSetupService extends ProjectOperatingSetupService {
  FakeProjectOperatingSetupService(this._setup);
  final ProjectOperatingSetup _setup;

  @override
  Future<ProjectOperatingSetup> get(String projectId) async => _setup;
}

/// Fake cho phép test kiểm soát thời điểm resolve của TỪNG project riêng
/// biệt (mỗi `projectId` có 1 `Completer` riêng) — dùng để mô phỏng race
/// condition: request của project A hoàn tất SAU request của project B dù
/// A được gọi trước.
class FakeDelayedProjectOperatingSetupService extends ProjectOperatingSetupService {
  final Map<String, Completer<ProjectOperatingSetup>> _completers = {};

  Completer<ProjectOperatingSetup> completerFor(String projectId) =>
      _completers.putIfAbsent(projectId, () => Completer<ProjectOperatingSetup>());

  @override
  Future<ProjectOperatingSetup> get(String projectId) => completerFor(projectId).future;
}

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

  test('selectProject loads operating setup for the chosen project', () async {
    final tasksController = TasksController();
    final fakeSetup = const ProjectOperatingSetup(
      projectId: 'p-1',
      workspaceId: 'w-1',
      status: OperatingSetupStatus.active,
      selectedStage: ProjectLifecycleStage.p0Discovery,
    );
    final controller = WorkOverviewController(
      tasksController: tasksController,
      projectOperatingSetupService: FakeProjectOperatingSetupService(fakeSetup),
    );

    await controller.selectProject('p-1');

    expect(controller.selectedProjectId.value, 'p-1');
    expect(controller.projectSetup.value?.status, OperatingSetupStatus.active);
    expect(controller.isProjectInfoLoading.value, isFalse);
    expect(controller.projectInfoError.value, isNull);
  });

  test('selectProject ignores a stale response after switching to another project', () async {
    final tasksController = TasksController();
    final fakeService = FakeDelayedProjectOperatingSetupService();
    final controller = WorkOverviewController(
      tasksController: tasksController,
      projectOperatingSetupService: fakeService,
    );

    // Bắt đầu chọn A, request của A CHƯA resolve.
    final futureA = controller.selectProject('p-a');
    // Đổi ngay sang B trong lúc A còn đang chờ.
    final futureB = controller.selectProject('p-b');

    // B (request mới hơn) resolve TRƯỚC.
    fakeService.completerFor('p-b').complete(
      const ProjectOperatingSetup(
        projectId: 'p-b',
        workspaceId: 'w-1',
        status: OperatingSetupStatus.active,
      ),
    );
    await futureB;

    expect(controller.selectedProjectId.value, 'p-b');
    expect(controller.projectSetup.value?.projectId, 'p-b');

    // A (request cũ, chậm) resolve SAU — không được phép ghi đè state của B.
    fakeService.completerFor('p-a').complete(
      const ProjectOperatingSetup(
        projectId: 'p-a',
        workspaceId: 'w-1',
        status: OperatingSetupStatus.notStarted,
      ),
    );
    await futureA;

    expect(controller.selectedProjectId.value, 'p-b');
    expect(controller.projectSetup.value?.projectId, 'p-b');
    expect(controller.isProjectInfoLoading.value, isFalse);
  });

  test('loadOkrAndTwelveWySummary computes average KR completion and reads execution score', () async {
    final controller = WorkOverviewController(
      tasksController: TasksController(),
      okrService: FakeOkrService(),
      twelveWyService: FakeTwelveWyService(),
    );

    await controller.loadOkrAndTwelveWySummary();

    expect(controller.okrCompletionRatio.value, 0.75); // avg(50/100, 100/100)
    expect(controller.twelveWyExecutionScore.value, 0.75);
    expect(controller.isOkrSummaryLoading.value, isFalse);
    expect(controller.okrSummaryError.value, isNull);
  });

  test('loadOkrAndTwelveWySummary sets isOkrSummaryLoading while pending', () async {
    final controller = WorkOverviewController(
      tasksController: TasksController(),
      okrService: FakeOkrService(),
      twelveWyService: FakeTwelveWyService(),
    );

    final future = controller.loadOkrAndTwelveWySummary();
    expect(controller.isOkrSummaryLoading.value, isTrue);

    await future;
    expect(controller.isOkrSummaryLoading.value, isFalse);
  });

  test(
    'loadOkrAndTwelveWySummary catches a thrown exception (vd lỗi secure-storage) '
    'into okrSummaryError thay vì ném ra ngoài unhandled',
    () async {
      final controller = WorkOverviewController(
        tasksController: TasksController(),
        okrService: ThrowingOkrService(),
        twelveWyService: FakeTwelveWyService(),
      );

      // Không được throw ra khỏi hàm — lỗi phải được bắt lại và phản ánh qua
      // `okrSummaryError`.
      await controller.loadOkrAndTwelveWySummary();

      expect(controller.okrSummaryError.value, isNotNull);
      expect(controller.isOkrSummaryLoading.value, isFalse);
      expect(controller.okrCompletionRatio.value, isNull);
    },
  );
}
