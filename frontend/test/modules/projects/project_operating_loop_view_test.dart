import 'package:flutter_test/flutter_test.dart';
import 'package:get/get.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:frontend/modules/projects/controllers/project_operating_loop_controller.dart';
import 'package:frontend/modules/projects/models/project_operating_loop.dart';
import 'package:frontend/modules/projects/views/project_operating_loop_view.dart';

void main() {
  testWidgets('renders loading and 4 operating loop tabs with populated data', (tester) async {
    // Task 13 — tab "Evidence & Decisions" giờ có thêm _ProjectLifecycleSection,
    // widget này tự đọc `workspace_id` qua SecureStorageService (SharedPreferences
    // cho key không-secret). Không seed mock value thì SharedPreferences.getInstance()
    // treo vô thời hạn (không throw, không timeout) — khớp với comment trong
    // secure_storage_service.dart rằng nhiều test khác cũng phải seed như thế này.
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

    // Provide populated loop data
    controller.loop.value = ProjectOperatingLoop(
      project: ProjectSummary(
        id: 'proj_1',
        workspaceId: 'ws_1',
        title: 'Launch Alpha',
        status: 'ACTIVE',
        createdAt: '2026-09-10T12:00:00Z',
        updatedAt: '2026-09-10T12:00:00Z',
      ),
      objectives: [
        LoopObjective(id: 'obj_1', title: 'Achieve PMF', status: 'active'),
      ],
      activeCycle: LoopActiveCycle(
        id: 'cycle_1',
        durationWeeks: 6,
        startDate: '2026-09-01',
        endDate: '2026-10-15',
        revision: 1,
        weeklyPlans: [
          LoopWeeklyPlan(
            id: 'wp_1',
            weekNo: 1,
            focus: 'Customer discovery',
            commitments: [
              LoopCommitment(
                id: 'com_1',
                title: '5 customer interviews',
                status: 'committed',
                tasks: [
                  LoopTask(
                    id: 'task_1',
                    title: 'Conduct user interview #1',
                    status: 'todo',
                    priority: 'high',
                  ),
                ],
              ),
            ],
          ),
        ],
      ),
      evidence: [
        LoopEvidence(id: 'ev_1', title: 'Interview transcript #1', status: 'approved', sourceType: 'interview'),
      ],
      decisions: [
        LoopDecision(id: 'dec_1', title: 'Pivot pricing model', status: 'approved'),
      ],
    );

    await tester.pumpAndSettle();

    // Verify Project Title
    expect(find.text('Launch Alpha'), findsOneWidget);

    // Verify 4 Tab labels exist
    expect(find.text('OKRs'), findsOneWidget);
    expect(find.text('Cycle & Weekly'), findsOneWidget);
    expect(find.text('Tasks'), findsOneWidget);
    expect(find.text('Evidence & Decisions'), findsOneWidget);

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
    expect(find.text('Week 1: 5 customer interviews'), findsOneWidget);
    expect(find.text('Conduct user interview #1'), findsOneWidget);

    // Tap on 'Evidence & Decisions' tab
    await tester.tap(find.text('Evidence & Decisions'));
    await tester.pumpAndSettle();
    expect(find.text('Interview transcript #1'), findsOneWidget);
    expect(find.text('Pivot pricing model'), findsOneWidget);

    Get.delete<ProjectOperatingLoopController>();
  });
}
