import 'package:flutter_test/flutter_test.dart';
import 'package:get/get.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:frontend/modules/projects/controllers/project_operating_loop_controller.dart';
import 'package:frontend/modules/projects/models/project_operating_loop.dart';
import 'package:frontend/modules/projects/views/project_operating_loop_view.dart';

void main() {
  testWidgets('renders loading and 4 operating loop tabs with populated real-shape data', (tester) async {
    // Task 4 (2026-09-14 remediation) — tab thứ 4 đổi tên từ
    // "Evidence & Decisions" (field không tồn tại ở backend) thành
    // "Lifecycle", nơi giờ đọc lifecycleStage/stageVersion trực tiếp từ
    // `controller.loop.value.project` thay vì round-trip
    // `ProjectService().getProjects()` riêng — vẫn cần seed `workspace_id`
    // vì `showExecutiveBoardStageSuggestionDialog` (được gọi sau khi
    // transition) đọc qua SecureStorageService.
    SharedPreferences.setMockInitialValues({'workspace_id': 'ws_1'});

    final controller = ProjectOperatingLoopController(projectId: 'proj_1');
    Get.put<ProjectOperatingLoopController>(controller);

    await tester.pumpWidget(
      const GetMaterialApp(
        home: ProjectOperatingLoopView(),
      ),
    );

    // Initial state: missing or loading
    expect(find.byType(ProjectOperatingLoopView), findsOneWidget);

    // Provide populated loop data matching the real server DTO shape.
    controller.loop.value = ProjectOperatingLoop(
      project: ProjectSummary(
        id: 'proj_1',
        workspaceId: 'ws_1',
        title: 'Launch Alpha',
        lifecycleStage: 'P2_SOLUTION_VALIDATION',
        stageVersion: 3,
        status: 'ACTIVE',
        createdAt: '2026-09-10T12:00:00Z',
      ),
      objectives: [
        LoopObjectiveTree(
          objective: LoopObjective(
            id: 'obj_1',
            workspaceId: 'ws_1',
            projectId: 'proj_1',
            title: 'Achieve PMF',
            status: 'active',
            createdAt: '2026-09-10T12:00:00Z',
            updatedAt: '2026-09-10T12:00:00Z',
          ),
          keyResults: const [],
        ),
      ],
      activeCycle: LoopActiveCycle(
        id: 'cycle_1',
        workspaceId: 'ws_1',
        projectId: 'proj_1',
        currentWeek: 1,
        durationWeeks: 6,
        visionStatement: 'Find PMF',
        status: 'active',
        timezone: 'UTC',
        startDate: '2026-09-01',
        endDate: '2026-10-15',
        createdAt: '2026-09-01T00:00:00Z',
        updatedAt: '2026-09-01T00:00:00Z',
      ),
      currentWeek: LoopWeek(
        id: 'week_1',
        workspaceId: 'ws_1',
        projectId: 'proj_1',
        cycleId: 'cycle_1',
        weekNo: 1,
        focus: 'Customer discovery',
        createdAt: '2026-09-01T00:00:00Z',
        updatedAt: '2026-09-01T00:00:00Z',
      ),
      commitments: [
        LoopCommitment(
          id: 'com_1',
          workspaceId: 'ws_1',
          projectId: 'proj_1',
          weeklyPlanId: 'week_1',
          title: '5 customer interviews',
          status: 'committed',
          purposeType: 'INITIATIVE',
          createdAt: '2026-09-01T00:00:00Z',
          updatedAt: '2026-09-01T00:00:00Z',
        ),
      ],
      tasks: [
        LoopTask(
          id: 'task_1',
          workspaceId: 'ws_1',
          projectId: 'proj_1',
          weeklyCommitmentId: 'com_1',
          title: 'Conduct user interview #1',
          status: 'todo',
          priority: 'high',
          timezone: 'UTC',
          createdAt: '2026-09-01T00:00:00Z',
          updatedAt: '2026-09-01T00:00:00Z',
        ),
      ],
    );

    await tester.pumpAndSettle();

    // Verify Project Title
    expect(find.text('Launch Alpha'), findsOneWidget);

    // Verify 4 Tab labels exist
    expect(find.text('OKRs'), findsOneWidget);
    expect(find.text('Cycle & Weekly'), findsOneWidget);
    expect(find.text('Tasks'), findsOneWidget);
    expect(find.text('Lifecycle'), findsOneWidget);

    // Verify first tab content (OKRs)
    expect(find.text('Achieve PMF'), findsOneWidget);

    // Tap on 'Cycle & Weekly' tab
    await tester.tap(find.text('Cycle & Weekly'));
    await tester.pumpAndSettle();
    expect(find.text('Active Cycle (6 Weeks)'), findsOneWidget);
    expect(find.text('Week 1: Customer discovery'), findsOneWidget);

    // Tap on 'Tasks' tab
    await tester.tap(find.text('Tasks'));
    await tester.pumpAndSettle();
    expect(find.text('5 customer interviews'), findsOneWidget);
    expect(find.text('Conduct user interview #1'), findsOneWidget);

    // Tap on 'Lifecycle' tab — reads directly from loaded loop, no evidence/
    // decisions phantom fields anywhere.
    await tester.tap(find.text('Lifecycle'));
    await tester.pumpAndSettle();
    expect(find.text('Giai đoạn hiện tại: P2_SOLUTION_VALIDATION'), findsOneWidget);

    Get.delete<ProjectOperatingLoopController>();
  });
}
