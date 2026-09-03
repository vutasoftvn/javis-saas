import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:get/get.dart';
import 'package:frontend/core/runtime/mutation_gate.dart';
import 'package:frontend/modules/tasks/controllers/tasks_controller.dart';
import 'package:frontend/modules/tasks/views/tasks_view.dart';
import 'package:frontend/modules/tasks/views/tabs/work_overview_tab.dart';

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
