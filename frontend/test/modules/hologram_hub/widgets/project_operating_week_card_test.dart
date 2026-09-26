import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/modules/hologram_hub/widgets/project_operating_week_card.dart';
import 'package:frontend/modules/projects/models/project_operating_loop.dart';

void main() {
  final testProjectSummary = ProjectSummary(
    id: 'proj-1',
    workspaceId: 'ws-1',
    title: 'Alpha Project',
    lifecycleStage: 'P0_DISCOVERY',
    stageVersion: 1,
    status: 'ACTIVE',
    createdAt: '2026-08-01T00:00:00.000Z',
  );

  testWidgets('(a) renders empty state when no active cycle exists', (tester) async {
    final loop = ProjectOperatingLoop(
      project: testProjectSummary,
      activeCycle: null,
    );

    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: ProjectOperatingWeekCard(operatingLoop: loop),
        ),
      ),
    );

    expect(find.byKey(const Key('operating_week_no_cycle')), findsOneWidget);
    expect(
      find.text('Dự án chưa có chu kỳ hoạt động (Operating Cycle) nào đang diễn ra.'),
      findsOneWidget,
    );
  });

  testWidgets('(b) renders Week 1 with commitments and incomplete/total task counts', (tester) async {
    final now = DateTime.now().toUtc().toIso8601String();
    final loop = ProjectOperatingLoop(
      project: testProjectSummary,
      activeCycle: LoopActiveCycle(
        id: 'cycle-1',
        workspaceId: 'ws-1',
        projectId: 'proj-1',
        currentWeek: 1,
        durationWeeks: 12,
        visionStatement: 'Find PMF',
        status: 'active',
        timezone: 'UTC',
        startDate: now,
        endDate: DateTime.now().toUtc().add(const Duration(days: 84)).toIso8601String(),
        createdAt: now,
        updatedAt: now,
      ),
      currentWeek: LoopWeek(
        id: 'week-1',
        workspaceId: 'ws-1',
        projectId: 'proj-1',
        cycleId: 'cycle-1',
        weekNo: 1,
        focus: 'Phỏng vấn 5 khách hàng B2B',
        createdAt: now,
        updatedAt: now,
      ),
      commitments: [
        LoopCommitment(
          id: 'com-1',
          workspaceId: 'ws-1',
          projectId: 'proj-1',
          weeklyPlanId: 'week-1',
          title: 'Khách hàng phân khúc Logistics',
          status: 'committed',
          purposeType: 'INITIATIVE',
          createdAt: now,
          updatedAt: now,
        ),
      ],
      tasks: [
        LoopTask(
          id: 't-1',
          workspaceId: 'ws-1',
          projectId: 'proj-1',
          weeklyCommitmentId: 'com-1',
          title: 'Soạn kịch bản',
          status: 'done',
          priority: 'high',
          timezone: 'UTC',
          createdAt: now,
          updatedAt: now,
        ),
        LoopTask(
          id: 't-2',
          workspaceId: 'ws-1',
          projectId: 'proj-1',
          weeklyCommitmentId: 'com-1',
          title: 'Liên hệ 10 cty',
          status: 'todo',
          priority: 'high',
          timezone: 'UTC',
          createdAt: now,
          updatedAt: now,
        ),
        LoopTask(
          id: 't-3',
          workspaceId: 'ws-1',
          projectId: 'proj-1',
          weeklyCommitmentId: 'com-1',
          title: 'Phỏng vấn cty A',
          status: 'todo',
          priority: 'medium',
          timezone: 'UTC',
          createdAt: now,
          updatedAt: now,
        ),
      ],
    );

    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: ProjectOperatingWeekCard(operatingLoop: loop),
        ),
      ),
    );

    expect(find.byKey(const Key('operating_week_card')), findsOneWidget);
    expect(find.text('Chu kỳ 12 tuần — Tuần 1'), findsOneWidget);
    expect(find.text('Phỏng vấn 5 khách hàng B2B'), findsOneWidget);
    expect(find.text('Khách hàng phân khúc Logistics'), findsOneWidget);
    // 2 todo tasks out of 3 tasks
    expect(find.text('2/3 việc'), findsOneWidget);
  });

  testWidgets('(c) renders truthful message when commitments list is empty', (tester) async {
    final now = DateTime.now().toUtc().toIso8601String();
    final loop = ProjectOperatingLoop(
      project: testProjectSummary,
      activeCycle: LoopActiveCycle(
        id: 'cycle-1',
        workspaceId: 'ws-1',
        projectId: 'proj-1',
        currentWeek: 1,
        durationWeeks: 12,
        visionStatement: 'Find PMF',
        status: 'active',
        timezone: 'UTC',
        startDate: now,
        endDate: DateTime.now().toUtc().add(const Duration(days: 84)).toIso8601String(),
        createdAt: now,
        updatedAt: now,
      ),
      currentWeek: LoopWeek(
        id: 'week-1',
        workspaceId: 'ws-1',
        projectId: 'proj-1',
        cycleId: 'cycle-1',
        weekNo: 1,
        createdAt: now,
        updatedAt: now,
      ),
      commitments: const [],
    );

    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: ProjectOperatingWeekCard(operatingLoop: loop),
        ),
      ),
    );

    expect(find.byKey(const Key('operating_week_card')), findsOneWidget);
    expect(
      find.text('Chưa có cam kết công việc nào trong tuần này.'),
      findsOneWidget,
    );
  });

  testWidgets('(d) renders error state and triggers onRetry callback', (tester) async {
    bool retried = false;

    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: ProjectOperatingWeekCard(
            operatingLoop: null,
            errorMessage: 'Network timeout reading loop',
            onRetry: () {
              retried = true;
            },
          ),
        ),
      ),
    );

    expect(find.byKey(const Key('operating_week_error')), findsOneWidget);
    expect(find.text('Network timeout reading loop'), findsOneWidget);

    final retryBtn = find.byKey(const Key('operating_week_retry_button'));
    expect(retryBtn, findsOneWidget);
    await tester.tap(retryBtn);
    await tester.pump();

    expect(retried, isTrue);
  });

  testWidgets('(e) separates P0 as title badge and displays accompanying Key Results', (tester) async {
    final now = DateTime.now().toUtc().toIso8601String();
    final loop = ProjectOperatingLoop(
      project: testProjectSummary,
      activeCycle: LoopActiveCycle(
        id: 'cycle-1',
        workspaceId: 'ws-1',
        projectId: 'proj-1',
        currentWeek: 1,
        durationWeeks: 2,
        visionStatement: 'Discovery phase',
        status: 'active',
        timezone: 'UTC',
        sourceObjectiveId: 'obj-1',
        startDate: now,
        createdAt: now,
        updatedAt: now,
      ),
      currentWeek: LoopWeek(
        id: 'week-1',
        workspaceId: 'ws-1',
        projectId: 'proj-1',
        cycleId: 'cycle-1',
        weekNo: 1,
        focus: '[P0 - Khám phá & Đánh giá cơ hội] Xác thực giải pháp cho Founder',
        createdAt: now,
        updatedAt: now,
      ),
      objectives: [
        LoopObjectiveTree(
          objective: LoopObjective(
            id: 'obj-1',
            workspaceId: 'ws-1',
            projectId: 'proj-1',
            title: 'Xác thực giải pháp',
            status: 'ACTIVE',
            createdAt: now,
            updatedAt: now,
          ),
          keyResults: [
            LoopKeyResultTree(
              keyResult: LoopKeyResult(
                id: 'kr-1',
                workspaceId: 'ws-1',
                objectiveId: 'obj-1',
                title: 'Phỏng vấn 15 founder',
                currentValue: 5,
                targetValue: 15,
                unit: 'founder',
                scoringType: 'NUMERIC',
                status: 'active',
                createdAt: now,
                updatedAt: now,
              ),
            ),
          ],
        ),
      ],
      commitments: const [],
    );

    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: ProjectOperatingWeekCard(operatingLoop: loop),
        ),
      ),
    );

    expect(find.text('P0 - Khám phá & Đánh giá cơ hội'), findsOneWidget);
    expect(find.text('Xác thực giải pháp cho Founder'), findsOneWidget);
    expect(find.text('Kết quả then chốt (Key Results):'), findsOneWidget);
    expect(find.text('Phỏng vấn 15 founder'), findsOneWidget);
    expect(find.text('5 / 15 founder'), findsOneWidget);
  });

  testWidgets('(f) renders compact badge for binary verification KR without 0/1 text', (tester) async {
    final now = DateTime.now().toUtc().toIso8601String();
    final loop = ProjectOperatingLoop(
      project: testProjectSummary,
      activeCycle: LoopActiveCycle(
        id: 'cycle-1',
        workspaceId: 'ws-1',
        projectId: 'proj-1',
        currentWeek: 1,
        durationWeeks: 2,
        visionStatement: 'Discovery phase',
        status: 'active',
        timezone: 'UTC',
        sourceObjectiveId: 'obj-1',
        startDate: now,
        createdAt: now,
        updatedAt: now,
      ),
      currentWeek: LoopWeek(
        id: 'week-1',
        workspaceId: 'ws-1',
        projectId: 'proj-1',
        cycleId: 'cycle-1',
        weekNo: 1,
        focus: '[P0 - Khám phá] Xác thực nhu cầu',
        createdAt: now,
        updatedAt: now,
      ),
      objectives: [
        LoopObjectiveTree(
          objective: LoopObjective(
            id: 'obj-1',
            workspaceId: 'ws-1',
            projectId: 'proj-1',
            title: 'Xác thực',
            status: 'ACTIVE',
            createdAt: now,
            updatedAt: now,
          ),
          keyResults: [
            LoopKeyResultTree(
              keyResult: LoopKeyResult(
                id: 'kr-1',
                workspaceId: 'ws-1',
                objectiveId: 'obj-1',
                title: 'Khách hàng chủ động tìm giải pháp',
                currentValue: 0,
                targetValue: 1,
                unit: 'đã kiểm chứng',
                scoringType: 'BOOLEAN',
                status: 'active',
                createdAt: now,
                updatedAt: now,
              ),
            ),
          ],
        ),
      ],
      commitments: const [],
    );

    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: ProjectOperatingWeekCard(operatingLoop: loop),
        ),
      ),
    );

    // In icon-only mode, the label is in the Tooltip message rather than on-screen text
    expect(find.text('Chưa kiểm chứng'), findsNothing);
    expect(find.byIcon(Icons.hourglass_empty_rounded), findsOneWidget);
    expect(
      find.byWidgetPredicate((w) => w is Tooltip && w.message == 'Chưa kiểm chứng'),
      findsOneWidget,
    );
    // 0 / 1 text must not appear
    expect(find.textContaining('0 / 1'), findsNothing);
  });
}
