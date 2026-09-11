import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/modules/hologram_hub/widgets/project_operating_week_card.dart';
import 'package:frontend/modules/projects/models/project_operating_loop.dart';

void main() {
  final testProjectSummary = ProjectSummary(
    id: 'proj-1',
    workspaceId: 'ws-1',
    title: 'Alpha Project',
    status: 'ACTIVE',
    createdAt: '2026-08-01T00:00:00.000Z',
    updatedAt: '2026-08-01T00:00:00.000Z',
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
        durationWeeks: 12,
        startDate: now,
        endDate: DateTime.now().toUtc().add(const Duration(days: 84)).toIso8601String(),
        revision: 1,
        weeklyPlans: [
          LoopWeeklyPlan(
            id: 'plan-1',
            weekNo: 1,
            focus: 'Phỏng vấn 5 khách hàng B2B',
            commitments: [
              LoopCommitment(
                id: 'com-1',
                title: 'Khách hàng phân khúc Logistics',
                status: 'committed',
                tasks: [
                  LoopTask(id: 't-1', title: 'Soạn kịch bản', status: 'done', priority: 'high'),
                  LoopTask(id: 't-2', title: 'Liên hệ 10 cty', status: 'todo', priority: 'high'),
                  LoopTask(id: 't-3', title: 'Phỏng vấn cty A', status: 'todo', priority: 'medium'),
                ],
              ),
            ],
          ),
        ],
      ),
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
        durationWeeks: 12,
        startDate: now,
        endDate: DateTime.now().toUtc().add(const Duration(days: 84)).toIso8601String(),
        revision: 1,
        weeklyPlans: [
          LoopWeeklyPlan(
            id: 'plan-1',
            weekNo: 1,
            commitments: [],
          ),
        ],
      ),
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
}
