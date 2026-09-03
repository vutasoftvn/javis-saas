import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:get/get.dart';
import 'package:frontend/core/runtime/mutation_gate.dart';
import 'package:frontend/data/models/project_operating_setup_model.dart';
import 'package:frontend/data/models/task_kanban_model.dart';
import 'package:frontend/modules/hologram_hub/controllers/founder_command_center_controller.dart';
import 'package:frontend/modules/strategy/services/project_operating_setup_service.dart';
import 'package:frontend/modules/tasks/controllers/tasks_controller.dart';
import 'package:frontend/modules/tasks/controllers/work_overview_controller.dart';
import 'package:frontend/modules/tasks/views/tasks_view.dart';
import 'package:frontend/modules/tasks/views/tabs/work_overview_tab.dart';

import '../controllers/work_overview_controller_test.dart' show FakeOkrService, FakeTwelveWyService;

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
    // Dùng fake OkrService/TwelveWyService — default constructor gọi network
    // thật qua ApiClient, không xác định (kể từ khi khối OKR/12WY có
    // isOkrSummaryLoading hiển thị CircularProgressIndicator, gọi network
    // thật trong widget test khiến pumpAndSettle() không bao giờ settle).
    Get.put<WorkOverviewController>(
      WorkOverviewController(
        tasksController: controller,
        okrService: FakeOkrService(),
        twelveWyService: FakeTwelveWyService(),
      ),
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
        okrService: FakeOkrService(),
        twelveWyService: FakeTwelveWyService(),
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

  testWidgets(
    'renders all 4 Tổng quan blocks with fake data and "Xem ở Kanban" điều hướng sang tab Kanban',
    (tester) async {
      tester.view.physicalSize = const Size(1700, 900);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);

      final now = DateTime.now();
      final today = DateTime(now.year, now.month, now.day).toIso8601String();

      final tasksController = TestTasksController(mutationGate: MockMutationGate());
      tasksController.isLoading.value = false;
      tasksController.tasks.assignAll([
        TaskKanbanModel(
          id: '1',
          title: 'Việc cần làm hôm nay',
          status: TaskKanbanStatus.todo,
          dueDate: today,
        ),
        TaskKanbanModel(
          id: '2',
          title: 'Việc đang làm',
          status: TaskKanbanStatus.inProgress,
        ),
      ]);
      Get.put<TasksController>(tasksController);

      // Dùng fake OkrService/TwelveWyService (tái dùng từ
      // work_overview_controller_test.dart) — KHÔNG dùng default constructor
      // vì default gọi network thật qua ApiClient.
      final workOverviewController = WorkOverviewController(
        tasksController: tasksController,
        okrService: FakeOkrService(),
        twelveWyService: FakeTwelveWyService(),
        projectOperatingSetupService: FakeProjectOperatingSetupService(),
      );
      Get.put<WorkOverviewController>(workOverviewController);

      final fcc = TestFounderCommandCenterController();
      fcc.projectsList.assignAll([
        {'id': 'p-1', 'title': 'Project 1'},
      ]);
      Get.put<FounderCommandCenterController>(fcc);

      await tester.pumpWidget(
        const GetMaterialApp(home: Scaffold(body: TasksView())),
      );
      await tester.pumpAndSettle();

      // Khối 1: thống kê trạng thái.
      expect(find.text('Cần làm'), findsWidgets);
      expect(find.text('Đang làm'), findsWidgets);

      // Khối 2: OKR/12WY rút gọn (đã tải thành công qua fake service, không
      // còn kẹt ở loading/'—').
      expect(find.text('OKR chu kỳ hiện tại'), findsOneWidget);
      expect(find.text('Điểm thực thi tuần (12WY)'), findsOneWidget);
      expect(find.text('75%'), findsNWidgets(2));

      // Khối 3: thông tin quản trị project.
      expect(find.text('Thông tin quản trị project'), findsOneWidget);

      // Khối 4: việc hôm nay — có nội dung thật (task có dueDate hôm nay).
      expect(find.text('Việc hôm nay'), findsOneWidget);
      expect(find.text('Việc cần làm hôm nay'), findsOneWidget);
      expect(find.text('Xem ở Kanban'), findsOneWidget);

      // Bấm "Xem ở Kanban" trong khối "Việc hôm nay" phải điều hướng sang tab
      // Kanban (index 1). `TabController.animateTo()` set `.index` NGAY LẬP
      // TỨC (đồng bộ) trước khi animation chạy — chỉ cần 1 `pump()` để xử lý
      // gesture tap, KHÔNG dùng `pumpAndSettle()` ở đây: bug tiền tồn tại
      // KHÔNG thuộc phạm vi finding này (`Obx` bọc `mutationPermission()`
      // trong `kanban_task_card.dart` báo "improper use of a GetX" khi thực
      // sự build 1 thẻ Kanban có task, gây RenderFlex overflow giả trong môi
      // trường test) sẽ nổ ra nếu để `TaskKanbanTab` build đầy đủ cột chứa
      // các task giả — không liên quan gì tới OKR/12WY hay điều hướng tab.
      final tabControllerBefore = DefaultTabController.of(
        tester.element(find.byType(WorkOverviewTab)),
      );
      expect(tabControllerBefore.index, 0);

      await tester.tap(find.text('Xem ở Kanban'));
      await tester.pump();

      final tabController = DefaultTabController.of(
        tester.element(find.byType(WorkOverviewTab)),
      );
      expect(tabController.index, 1);
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
