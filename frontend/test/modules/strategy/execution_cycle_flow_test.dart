import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/core/network/api_result.dart';
import 'package:frontend/modules/strategy/models/mvp_strategy_models.dart';
import 'package:frontend/modules/strategy/services/strategy_mvp_client.dart';
import 'package:frontend/modules/strategy/services/twelve_wy_service.dart';
import 'package:frontend/modules/strategy/views/tabs/weekly_review_tab.dart';
import 'package:frontend/modules/strategy/views/twelve_week_year_view.dart';
import 'package:frontend/modules/strategy/controllers/strategy_controller.dart';
import 'package:get/get.dart';

class MockStrategyMvpClientForFlow implements StrategyMvpClient {
  final MvpExecutionCycleView cycleView;
  final List<MvpWeeklyPlan> plans;
  final List<MvpWeeklyCommitment> commitments;

  MockStrategyMvpClientForFlow({
    required this.cycleView,
    required this.plans,
    required this.commitments,
  });

  @override
  Future<ApiResult<MvpExecutionCycleView>> getExecutionCycleView({
    required String projectId,
    String? cycleId,
  }) async {
    return ApiSuccess(
      data: cycleView,
      meta: ApiResponseMeta(dataState: ApiDataState.populated, observedAt: DateTime.now()),
    );
  }

  @override
  Future<ApiResult<List<MvpWeeklyPlan>>> listTwelveWeekPlans() async {
    return ApiSuccess(
      data: plans,
      meta: ApiResponseMeta(dataState: ApiDataState.populated, observedAt: DateTime.now()),
    );
  }

  @override
  Future<ApiResult<List<MvpWeeklyCommitment>>> listTwelveWeekCommitments() async {
    return ApiSuccess(
      data: commitments,
      meta: ApiResponseMeta(dataState: ApiDataState.populated, observedAt: DateTime.now()),
    );
  }

  @override
  Future<ApiResult<MvpWeeklyPlan>> updateWeeklyPlan({
    required String id,
    double? executionScore,
    double? outcomeScore,
    String? reflection,
  }) async {
    final existing = plans.firstWhere((p) => p.id == id);
    return ApiSuccess(
      data: MvpWeeklyPlan(
        id: existing.id,
        workspaceId: existing.workspaceId,
        cycleId: existing.cycleId,
        weekNo: existing.weekNo,
        executionScore: executionScore,
        outcomeScore: outcomeScore,
        reflection: reflection,
        createdAt: existing.createdAt,
      ),
      meta: ApiResponseMeta(dataState: ApiDataState.populated, observedAt: DateTime.now()),
    );
  }

  @override
  noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

void main() {
  setUp(() {
    Get.reset();
  });

  group('Execution Cycle Flow & Presentation Tests', () {
    testWidgets('Execution Cycle View displays flexible N-week cycle and removes mandatory week 13 copy', (tester) async {
      tester.view.physicalSize = const Size(1280, 800);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);

      final controller = Get.put(StrategyController());
      controller.twelveWeekCycles.value = [
        {
          'id': 'cycle-501',
          'theme': 'Tìm 5 pilot',
          'duration_weeks': 6,
          'current_week': 2,
          'start_date': '2026-09-07T00:00:00Z',
          'end_date': '2026-10-18T23:59:59Z',
          'status': 'ACTIVE',
        }
      ];
      controller.weeklyPlans.value = [
        {
          'id': 'plan-1',
          'week_no': 2,
          'focus': 'Triển khai onboarding pilot',
          'start_date': '2026-09-14T00:00:00Z',
          'end_date': '2026-09-20T23:59:59Z',
        }
      ];
      controller.weeklyCommitments.value = [];
      controller.isLoading.value = false;

      await tester.pumpWidget(
        const GetMaterialApp(
          home: Scaffold(
            body: TwelveWeekYearView(),
          ),
        ),
      );
      await tester.pumpAndSettle();

      // Verify Flexible Cycle presentation
      expect(find.text('Kế hoạch Chu kỳ Thực thi'), findsOneWidget);
      expect(find.text('Tìm 5 pilot'), findsOneWidget);
      expect(find.textContaining('6 tuần'), findsOneWidget);
      expect(find.text('TUẦN 2'), findsOneWidget);

      // Verify mandatory week 13 copy is absent
      expect(find.textContaining('Tuần 13 là bắt buộc'), findsNothing);
      expect(find.byKey(const ValueKey('cycle-save-error')), findsNothing);
    });

    testWidgets('WeeklyReviewTab loads plans and persists review without week 13 requirement', (tester) async {
      final mockPlans = [
        const MvpWeeklyPlan(
          id: 'plan-1',
          workspaceId: '100',
          cycleId: 'cycle-501',
          weekNo: 2,
          focus: 'Onboarding 5 pilot khách hàng',
          createdAt: '2026-09-07T00:00:00Z',
        ),
      ];
      final mockCommitments = [
        const MvpWeeklyCommitment(
          id: 'commit-1',
          workspaceId: '100',
          weeklyPlanId: 'plan-1',
          title: 'Phỏng vấn 3 khách hàng',
          status: 'done',
          createdAt: '2026-09-07T00:00:00Z',
        ),
      ];

      final mockClient = MockStrategyMvpClientForFlow(
        cycleView: const MvpExecutionCycleView(
          cycle: MvpExecutionCycleSummary(
            id: 'cycle-501',
            displayName: 'Tìm 5 pilot',
            durationWeeks: 6,
            startLocalDate: '2026-09-07',
            endLocalDateExclusive: '2026-10-19',
            timezone: 'Asia/Ho_Chi_Minh',
            revision: 1,
            status: 'ACTIVE',
          ),
          currentWeek: 2,
          weeklyPlans: [],
          commitments: [],
          linkedKrs: [],
          executionScore: 1.0,
          outcomeProgress: 0.5,
          dataIssues: [],
          allowedActions: ['weekly.plan.edit'],
        ),
        plans: mockPlans,
        commitments: mockCommitments,
      );

      final service = TwelveWyService(client: mockClient);

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: WeeklyReviewTab(service: service),
          ),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.textContaining('Tuần 2'), findsWidgets);
      expect(find.text('Onboarding 5 pilot khách hàng'), findsOneWidget);
      expect(find.text('Phỏng vấn 3 khách hàng'), findsOneWidget);
      expect(find.textContaining('Tuần 13 là bắt buộc'), findsNothing);
    });
  });
}
