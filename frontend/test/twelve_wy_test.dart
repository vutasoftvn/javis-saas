import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/data/models/twelve_wy_model.dart';
import 'package:frontend/modules/hologram_hub/widgets/twelve_wy/weekly_execution_gauge.dart';
import 'package:frontend/modules/hologram_hub/widgets/twelve_wy/tactical_item_card.dart';
import 'package:frontend/modules/hologram_hub/widgets/twelve_wy/twelve_week_timeline_bar.dart';

void main() {
  group('COSA 12-Week Year Models Test', () {
    test('TacticalItemModel fromJson deserialization', () {
      final json = {
        'id': 9001,
        'workspace_id': 1,
        'project_id': 2,
        'cycle_id': 3,
        'week_number': 1,
        'title': 'Phỏng vấn 10 khách hàng',
        'description': 'Kiểm chứng vấn đề B2B',
        'lead_indicator_name': 'Số cuộc gọi',
        'target_count': 10,
        'actual_count': 7,
        'status': 'IN_PROGRESS',
        'owner_role': 'Founder',
        'completed_at': null,
        'created_at': '2026-08-01T00:00:00',
      };
      final model = TacticalItemModel.fromJson(json);
      expect(model.id, 9001);
      expect(model.title, 'Phỏng vấn 10 khách hàng');
      expect(model.targetCount, 10);
      expect(model.actualCount, 7);
      expect(model.isDone, isFalse);
      expect(model.progressRatio, closeTo(0.7, 0.01));
    });

    test('TacticalItemModel isDone when actual >= target', () {
      final json = {
        'id': 9002,
        'workspace_id': 1,
        'project_id': 2,
        'cycle_id': 3,
        'week_number': 2,
        'title': 'Hoàn thành prototype',
        'description': '',
        'lead_indicator_name': 'Số màn hình',
        'target_count': 5,
        'actual_count': 5,
        'status': 'DONE',
        'owner_role': 'CTO',
        'completed_at': '2026-08-10T00:00:00',
        'created_at': '2026-08-01T00:00:00',
      };
      final model = TacticalItemModel.fromJson(json);
      expect(model.isDone, isTrue);
      expect(model.progressRatio, 1.0);
    });

    test('TwelveWeekCycleModel fromJson deserialization', () {
      final json = {
        'id': 100,
        'workspace_id': 1,
        'project_id': 2,
        'theme': 'Chu Kỳ Kiểm Chứng',
        'title': null,
        'vision_statement': 'Đạt Product-Market Fit',
        'stage_at_start': 'S1_PROBLEM_VALIDATION',
        'current_week': 3,
        'duration_weeks': 12,
        'status': 'ACTIVE',
        'overall_execution_score': 75.0,
        'start_date': null,
        'end_date': null,
        'created_at': '2026-08-01T00:00:00',
      };
      final model = TwelveWeekCycleModel.fromJson(json);
      expect(model.id, 100);
      expect(model.title, 'Chu Kỳ Kiểm Chứng');
      expect(model.currentWeek, 3);
      expect(model.totalWeeks, 12);
      expect(model.overallExecutionScore, 75.0);
    });

    test('TwelveWeekCycleModel supports custom total_weeks', () {
      final json = {
        'id': 101,
        'workspace_id': 1,
        'project_id': 2,
        'theme': 'Chu Kỳ 4 Tuần Sprint',
        'title': null,
        'vision_statement': 'Sprint nhanh',
        'stage_at_start': 'S0_IDEA_VALIDATION',
        'current_week': 1,
        'duration_weeks': 4,
        'status': 'ACTIVE',
        'overall_execution_score': 0.0,
        'start_date': null,
        'end_date': null,
        'created_at': '2026-08-01T00:00:00',
      };
      final model = TwelveWeekCycleModel.fromJson(json);
      expect(model.totalWeeks, 4);
    });

    test('WeeklyReviewModel fromJson deserialization', () {
      final json = {
        'id': 50,
        'workspace_id': 1,
        'project_id': 2,
        'cycle_id': 3,
        'week_number': 1,
        'execution_score': 88.5,
        'total_planned': 8,
        'total_completed': 7,
        'key_breakthroughs': ['Hoàn thành phỏng vấn'],
        'root_cause_blocks': ['Khó tiếp cận CTO'],
        'ai_recommendations': ['Tiếp tục duy trì nhịp độ'],
        'created_at': '2026-08-07T00:00:00',
      };
      final model = WeeklyReviewModel.fromJson(json);
      expect(model.executionScore, 88.5);
      expect(model.keyBreakthroughs.length, 1);
      expect(model.aiRecommendations.first, 'Tiếp tục duy trì nhịp độ');
    });
  });

  group('COSA 12-Week Year Widgets Test', () {
    testWidgets('WeeklyExecutionGauge renders score and week', (tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: SizedBox(
              width: 400,
              child: WeeklyExecutionGauge(score: 88.0, weekNumber: 3),
            ),
          ),
        ),
      );
      expect(find.text('88%'), findsOneWidget);
      expect(find.text('Tuần 3'), findsOneWidget);
      expect(find.textContaining('Xuất Sắc'), findsOneWidget);
    });

    testWidgets('WeeklyExecutionGauge shows warning color when <60%', (tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: SizedBox(
              width: 400,
              child: WeeklyExecutionGauge(score: 45.0, weekNumber: 2),
            ),
          ),
        ),
      );
      expect(find.text('45%'), findsOneWidget);
      expect(find.textContaining('Cảnh Báo'), findsOneWidget);
    });

    testWidgets('TacticalItemCard renders title and lead indicator', (tester) async {
      final tactic = TacticalItemModel(
        id: 1,
        workspaceId: 1,
        projectId: 2,
        cycleId: 3,
        weekNumber: 1,
        title: 'Phỏng vấn 10 founder',
        description: 'Kiểm chứng vấn đề',
        leadIndicatorName: 'Số cuộc gọi',
        targetCount: 10,
        actualCount: 4,
        status: 'IN_PROGRESS',
        ownerRole: 'Founder',
        createdAt: DateTime.now(),
      );

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: SizedBox(
              width: 400,
              child: TacticalItemCard(tactic: tactic),
            ),
          ),
        ),
      );

      expect(find.text('Phỏng vấn 10 founder'), findsOneWidget);
      expect(find.text('Số cuộc gọi'), findsOneWidget);
      expect(find.text('4 / 10'), findsOneWidget);
    });

    testWidgets('TwelveWeekTimelineBar renders all weeks', (tester) async {
      final scores = {for (int i = 1; i <= 12; i++) i: i <= 3 ? 90.0 : 0.0};
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: SizedBox(
              width: 700,
              child: TwelveWeekTimelineBar(
                currentWeek: 3,
                selectedWeek: 3,
                weeklyScores: scores,
                onSelectWeek: (_) {},
              ),
            ),
          ),
        ),
      );

      expect(find.text('W1'), findsOneWidget);
      expect(find.text('W12'), findsOneWidget);
    });
  });
}
