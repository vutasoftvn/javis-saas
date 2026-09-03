import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:get/get.dart';
import 'package:frontend/core/runtime/mutation_gate.dart';
import 'package:frontend/data/models/project_operating_setup_model.dart';
import 'package:frontend/modules/hologram_hub/controllers/founder_command_center_controller.dart';
import 'package:frontend/modules/strategy/services/project_operating_setup_service.dart';
import 'package:frontend/modules/tasks/controllers/tasks_controller.dart';
import 'package:frontend/modules/tasks/controllers/work_overview_controller.dart';
import 'package:frontend/modules/tasks/views/tasks_view.dart';
import 'package:frontend/modules/tasks/views/tabs/work_overview_tab.dart';

/// `WorkOverviewTab` (Task 3) đọc `FounderCommandCenterController.projectsList`
/// qua `Get.find` — override `loadDashboardData()` để tránh gọi network thật
/// trong test (tương tự `TestTasksController.loadTasks()` bên dưới).
class TestFounderCommandCenterController extends FounderCommandCenterController {
  @override
  Future<void> loadDashboardData() async {}
}

class FakeProjectOperatingSetupService extends ProjectOperatingSetupService {
  @override
  Future<ProjectOperatingSetup> get(String projectId) async => ProjectOperatingSetup(
        projectId: projectId,
        workspaceId: 'w-1',
        status: OperatingSetupStatus.active,
      );
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() {
    Get.reset();
    Get.testMode = true;
  });

  testWidgets('has Tổng quan and Kanban tabs, Kanban shows all 5 columns', (
    tester,
  ) async {
    tester.view.physicalSize = const Size(1700, 900);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    final controller = TestTasksController(mutationGate: MockMutationGate());
    controller.isLoading.value = false;
    Get.put<TasksController>(controller);
    Get.put<WorkOverviewController>(
      WorkOverviewController(tasksController: controller),
    );
    Get.put<FounderCommandCenterController>(
      TestFounderCommandCenterController(),
    );

    await tester.pumpWidget(
      const GetMaterialApp(home: Scaffold(body: TasksView())),
    );
    await tester.pump();

    expect(find.text('Tổng quan'), findsOneWidget);
    expect(find.text('Kanban'), findsOneWidget);
    expect(find.byType(WorkOverviewTab), findsOneWidget);

    await tester.tap(find.text('Kanban'));
    await tester.pumpAndSettle();

    for (final title in [
      'Cần làm',
      'Đang làm',
      'Chờ duyệt',
      'Tạm dừng / Nghẽn',
      'Hoàn thành',
    ]) {
      expect(find.text(title), findsWidgets);
    }
  });

  testWidgets(
    'project dropdown falls back to first project when selectedProjectId is stale',
    (tester) async {
      tester.view.physicalSize = const Size(1700, 900);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);

      final tasksController = TestTasksController(mutationGate: MockMutationGate());
      tasksController.isLoading.value = false;
      Get.put<TasksController>(tasksController);

      final workOverviewController = WorkOverviewController(
        tasksController: tasksController,
        projectOperatingSetupService: FakeProjectOperatingSetupService(),
      );
      // Mô phỏng đúng finding 1: `selectedProjectId` trỏ tới 1 project KHÔNG
      // còn nằm trong `projectsList` hiện tại (vd danh sách bị `assignAll`
      // lại ở nơi khác trong lúc đang chọn project đó).
      workOverviewController.selectedProjectId.value = 'p-stale';
      Get.put<WorkOverviewController>(workOverviewController);

      final fcc = TestFounderCommandCenterController();
      fcc.projectsList.assignAll([
        {'id': 'p-1', 'title': 'Project 1'},
        {'id': 'p-2', 'title': 'Project 2'},
      ]);
      Get.put<FounderCommandCenterController>(fcc);

      // Không được throw/assert khi build `DropdownButton` với `value` lệch
      // khỏi `items` — đây chính là bug ở finding 1 nếu chưa có guard.
      await tester.pumpWidget(
        const GetMaterialApp(home: Scaffold(body: TasksView())),
      );
      await tester.pumpAndSettle();

      expect(tester.takeException(), isNull);
      // Guard phải tự sửa lại lựa chọn về project đầu tiên hợp lệ.
      expect(workOverviewController.selectedProjectId.value, 'p-1');
      expect(find.text('Project 1'), findsWidgets);
    },
  );
}

class MockMutationGate implements MutationGate {
  @override
  MutationPermission check({required bool isMutation}) => MutationPermission.allowed;
}

class TestTasksController extends TasksController {
  TestTasksController({super.mutationGate});

  @override
  Future<void> loadTasks() async {
    // Không gọi network thật trong test — tránh isLoading treo mãi ở true
    // khiến pumpAndSettle() timeout. onInit() gốc (super) vẫn được gọi để
    // thỏa @mustCallSuper, chỉ loadTasks() bị vô hiệu hóa.
  }
}
