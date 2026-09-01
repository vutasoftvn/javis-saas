import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/core/network/api_result.dart';
import 'package:frontend/modules/strategy/services/strategy_mvp_client.dart';
import 'package:frontend/modules/strategy/services/twelve_wy_service.dart';
import 'package:frontend/modules/strategy/models/mvp_strategy_models.dart';

// Helper để dựng ApiSuccess/ApiFailureDetail thật gọn trong test (2 field bắt buộc
// meta/message không liên quan tới hành vi được kiểm chứng ở đây).
ApiSuccess<T> _success<T>(T data) => ApiSuccess(
      data: data,
      meta: ApiResponseMeta(dataState: ApiDataState.populated, observedAt: DateTime.now()),
    );

ApiFailureDetail _failureDetail(ApiFailureCode code) =>
    ApiFailureDetail(code: code, message: 'test failure');

// Mock implementation of StrategyMvpClient
class MockStrategyMvpClient implements StrategyMvpClient {
  Future<ApiResult<List<MvpTwelveWeekCycle>>> Function()? _listTwelveWeekCyclesImpl;
  Future<ApiResult<List<MvpWeeklyPlan>>> Function()? _listTwelveWeekPlansImpl;
  Future<ApiResult<List<MvpWeeklyCommitment>>> Function()? _listTwelveWeekCommitmentsImpl;

  void setListTwelveWeekCyclesResult(Future<ApiResult<List<MvpTwelveWeekCycle>>> result) {
    _listTwelveWeekCyclesImpl = () => result;
  }

  void setListTwelveWeekPlansResult(Future<ApiResult<List<MvpWeeklyPlan>>> result) {
    _listTwelveWeekPlansImpl = () => result;
  }

  void setListTwelveWeekCommitmentsResult(Future<ApiResult<List<MvpWeeklyCommitment>>> result) {
    _listTwelveWeekCommitmentsImpl = () => result;
  }

  @override
  Future<ApiResult<List<MvpTwelveWeekCycle>>> listTwelveWeekCycles() async {
    if (_listTwelveWeekCyclesImpl != null) {
      return _listTwelveWeekCyclesImpl!();
    }
    return ApiFailure<List<MvpTwelveWeekCycle>>(
      _failureDetail(ApiFailureCode.unknown),
    );
  }

  @override
  Future<ApiResult<List<MvpWeeklyPlan>>> listTwelveWeekPlans() async {
    if (_listTwelveWeekPlansImpl != null) {
      return _listTwelveWeekPlansImpl!();
    }
    return ApiFailure<List<MvpWeeklyPlan>>(
      _failureDetail(ApiFailureCode.unknown),
    );
  }

  @override
  Future<ApiResult<List<MvpWeeklyCommitment>>> listTwelveWeekCommitments() async {
    if (_listTwelveWeekCommitmentsImpl != null) {
      return _listTwelveWeekCommitmentsImpl!();
    }
    return ApiFailure<List<MvpWeeklyCommitment>>(
      _failureDetail(ApiFailureCode.unknown),
    );
  }

  // Placeholder for other StrategyMvpClient methods (not tested in this file)
  @override
  noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

void main() {
  group('TwelveWyService - Cycles', () {
    test('listCyclesResult returns ApiResult from client', () async {
      final mockClient = MockStrategyMvpClient();
      final cycles = [
        MvpTwelveWeekCycle(
          id: '1',
          workspaceId: '123',
          theme: 'Q1 Sprint',
          visionStatement: 'Build MVP',
          stageAtStart: 'P1_PROBLEM_VALIDATION',
          currentWeek: 5,
          durationWeeks: 12,
          overallExecutionScore: 0.85,
          status: 'active',
          createdAt: '2026-01-01T00:00:00Z',
        ),
      ];
      mockClient.setListTwelveWeekCyclesResult(Future.value(_success(cycles)));

      final service = TwelveWyService(client: mockClient);
      final result = await service.listCyclesResult();

      expect(result, isA<ApiSuccess>());
      if (result is ApiSuccess) {
        expect(result.dataOrNull!, hasLength(1));
        expect(result.dataOrNull!.first.theme, 'Q1 Sprint');
      }
    });

    test('listCyclesResult returns failure when client fails', () async {
      final mockClient = MockStrategyMvpClient();
      mockClient.setListTwelveWeekCyclesResult(
        Future.value(
          ApiFailure<List<MvpTwelveWeekCycle>>(
            _failureDetail(ApiFailureCode.notFound),
          ),
        ),
      );

      final service = TwelveWyService(client: mockClient);
      final result = await service.listCyclesResult();

      expect(result, isA<ApiFailure>());
    });

    test('getCycles returns mapped TwelveWeekCycleModel list', () async {
      final mockClient = MockStrategyMvpClient();
      final mvpCycles = [
        MvpTwelveWeekCycle(
          id: '1',
          workspaceId: '123',
          theme: 'Q1 Sprint',
          visionStatement: 'Build MVP',
          stageAtStart: 'P1_PROBLEM_VALIDATION',
          currentWeek: 5,
          durationWeeks: 12,
          overallExecutionScore: 0.85,
          status: 'active',
          createdAt: '2026-01-01T00:00:00Z',
        ),
      ];
      mockClient.setListTwelveWeekCyclesResult(Future.value(_success(mvpCycles)));

      final service = TwelveWyService(client: mockClient);
      final cycles = await service.getCycles();

      expect(cycles, hasLength(1));
      expect(cycles.first.id, 1);
      expect(cycles.first.title, 'Q1 Sprint');
      expect(cycles.first.currentWeek, 5);
      expect(cycles.first.totalWeeks, 12);
      expect(cycles.first.overallExecutionScore, 0.85);
    });

    test('getCycles returns empty list on API failure', () async {
      final mockClient = MockStrategyMvpClient();
      mockClient.setListTwelveWeekCyclesResult(
        Future.value(
          ApiFailure<List<MvpTwelveWeekCycle>>(
            _failureDetail(ApiFailureCode.notFound),
          ),
        ),
      );

      final service = TwelveWyService(client: mockClient);
      final cycles = await service.getCycles();

      expect(cycles, isEmpty);
    });

    test('getCycles handles parse errors gracefully', () async {
      final mockClient = MockStrategyMvpClient();
      final mvpCycles = [
        MvpTwelveWeekCycle(
          id: 'invalid-id', // Will fail int.tryParse, should return 0
          workspaceId: 'invalid-workspace',
          theme: null,
          visionStatement: '',
          stageAtStart: '',
          currentWeek: 0,
          durationWeeks: 12,
          overallExecutionScore: 0,
          status: '',
          createdAt: '2026-01-01T00:00:00Z',
        ),
      ];
      mockClient.setListTwelveWeekCyclesResult(Future.value(_success(mvpCycles)));

      final service = TwelveWyService(client: mockClient);
      final cycles = await service.getCycles();

      expect(cycles, hasLength(1));
      expect(cycles.first.id, 0); // fallback for invalid parse
      expect(cycles.first.title, 'Chu Kỳ 12 Tuần'); // default when theme is null
    });
  });

  group('TwelveWyService - Dashboard', () {
    test('getDashboard returns dashboard model when cycles exist', () async {
      final mockClient = MockStrategyMvpClient();
      final mvpCycles = [
        MvpTwelveWeekCycle(
          id: '1',
          workspaceId: '123',
          theme: 'Q1 Sprint',
          visionStatement: 'Build MVP',
          stageAtStart: 'P1_PROBLEM_VALIDATION',
          currentWeek: 5,
          durationWeeks: 12,
          overallExecutionScore: 0.85,
          status: 'active',
          createdAt: '2026-01-01T00:00:00Z',
        ),
      ];
      mockClient.setListTwelveWeekCyclesResult(Future.value(_success(mvpCycles)));

      final service = TwelveWyService(client: mockClient);
      final dashboard = await service.getDashboard(1);

      expect(dashboard, isNotNull);
      expect(dashboard!.cycle.title, 'Q1 Sprint');
      expect(dashboard.currentWeek, 5);
      expect(dashboard.currentWeekExecutionScore, 0.85);
      expect(dashboard.tacticsByWeek, isEmpty);
      expect(dashboard.weeklyScores, isEmpty);
    });

    test('getDashboard returns null when no cycles exist', () async {
      final mockClient = MockStrategyMvpClient();
      mockClient.setListTwelveWeekCyclesResult(Future.value(_success([])));

      final service = TwelveWyService(client: mockClient);
      final dashboard = await service.getDashboard(1);

      expect(dashboard, isNull);
    });

    test('getDashboard returns null on API failure', () async {
      final mockClient = MockStrategyMvpClient();
      mockClient.setListTwelveWeekCyclesResult(
        Future.value(
          ApiFailure<List<MvpTwelveWeekCycle>>(
            _failureDetail(ApiFailureCode.unavailable),
          ),
        ),
      );

      final service = TwelveWyService(client: mockClient);
      final dashboard = await service.getDashboard(1);

      expect(dashboard, isNull);
    });
  });

  group('TwelveWyService - Cycle Creation', () {
    test('createOrGetCycle returns first existing cycle', () async {
      final mockClient = MockStrategyMvpClient();
      final mvpCycles = [
        MvpTwelveWeekCycle(
          id: '1',
          workspaceId: '123',
          theme: 'Existing Cycle',
          visionStatement: '',
          stageAtStart: '',
          currentWeek: 0,
          durationWeeks: 12,
          overallExecutionScore: 0,
          status: '',
          createdAt: '2026-01-01T00:00:00Z',
        ),
      ];
      mockClient.setListTwelveWeekCyclesResult(Future.value(_success(mvpCycles)));

      final service = TwelveWyService(client: mockClient);
      final cycle = await service.createOrGetCycle(
        1,
        title: 'New Title',
        visionStatement: 'New Vision',
      );

      expect(cycle, isNotNull);
      expect(cycle!.title, 'Existing Cycle'); // Returns existing, ignores parameters
    });

    test('createOrGetCycle returns null when no cycles exist and API fails', () async {
      final mockClient = MockStrategyMvpClient();
      mockClient.setListTwelveWeekCyclesResult(
        Future.value(
          ApiFailure<List<MvpTwelveWeekCycle>>(
            _failureDetail(ApiFailureCode.notFound),
          ),
        ),
      );

      final service = TwelveWyService(client: mockClient);
      final cycle = await service.createOrGetCycle(
        1,
        title: 'New Cycle',
      );

      expect(cycle, isNull);
    });
  });

  group('TwelveWyService - Tactics', () {
    test('createTactic creates TacticalItemModel with provided data', () async {
      final service = TwelveWyService();

      final tactic = await service.createTactic(
        projectId: 1,
        cycleId: 1,
        weekNumber: 3,
        title: 'User Research',
        description: 'Interview 10 customers',
        leadIndicatorName: 'Interviews Completed',
        targetCount: 10,
        actualCount: 0,
        status: 'PLANNED',
        ownerRole: 'Founder',
      );

      expect(tactic, isNotNull);
      expect(tactic!.title, 'User Research');
      expect(tactic.weekNumber, 3);
      expect(tactic.leadIndicatorName, 'Interviews Completed');
      expect(tactic.targetCount, 10);
      expect(tactic.status, 'PLANNED');
    });

    test('createTactic uses default values for optional fields', () async {
      final service = TwelveWyService();

      final tactic = await service.createTactic(
        projectId: 1,
        weekNumber: 1,
        title: 'Quick Task',
        leadIndicatorName: 'Task Count',
      );

      expect(tactic, isNotNull);
      expect(tactic!.description, ''); // empty default
      expect(tactic.targetCount, 1); // default
      expect(tactic.actualCount, 0); // default
      expect(tactic.status, 'PLANNED'); // default
      expect(tactic.ownerRole, 'Founder'); // default
    });

    test('createTactic handles dynamic projectId conversion', () async {
      final service = TwelveWyService();

      final tactic = await service.createTactic(
        projectId: '123', // string
        weekNumber: 1,
        title: 'Task',
        leadIndicatorName: 'Count',
      );

      expect(tactic, isNotNull);
      expect(tactic!.projectId, 123); // converted to int
    });
  });

  group('TwelveWyService - Tactic Updates', () {
    test('updateTactic returns null (not implemented)', () async {
      final service = TwelveWyService();

      final result = await service.updateTactic(
        tacticId: 1,
        actualCount: 5,
        status: 'DONE',
      );

      expect(result, isNull);
    });
  });

  group('TwelveWyService - Weekly Review', () {
    test('generateWeeklyReview returns null (not implemented)', () async {
      final service = TwelveWyService();

      final result = await service.generateWeeklyReview(
        cycleId: 1,
        weekNumber: 5,
      );

      expect(result, isNull);
    });
  });

  group('TwelveWyService - Plans & Commitments', () {
    test('getWeeklyPlans returns ApiResult from client', () async {
      final mockClient = MockStrategyMvpClient();
      final plans = [
        MvpWeeklyPlan(
          id: 'plan-1',
          workspaceId: '123',
          cycleId: '1',
          weekNo: 1,
          focus: 'Launch Planning',
          createdAt: '2026-01-01T00:00:00Z',
        ),
      ];
      mockClient.setListTwelveWeekPlansResult(Future.value(_success(plans)));

      final service = TwelveWyService(client: mockClient);
      final result = await service.getWeeklyPlans();

      expect(result, isA<ApiSuccess>());
      if (result is ApiSuccess) {
        expect(result.dataOrNull!, hasLength(1));
        expect(result.dataOrNull!.first.focus, 'Launch Planning');
      }
    });

    test('getWeeklyCommitments returns ApiResult from client', () async {
      final mockClient = MockStrategyMvpClient();
      final commitments = [
        MvpWeeklyCommitment(
          id: 'commit-1',
          workspaceId: '123',
          weeklyPlanId: 'plan-1',
          title: 'Weekly commitment',
          status: 'pending',
          createdAt: '2026-01-01T00:00:00Z',
        ),
      ];
      mockClient.setListTwelveWeekCommitmentsResult(
        Future.value(_success(commitments)),
      );

      final service = TwelveWyService(client: mockClient);
      final result = await service.getWeeklyCommitments();

      expect(result, isA<ApiSuccess>());
      if (result is ApiSuccess) {
        expect(result.dataOrNull!, hasLength(1));
        expect(result.dataOrNull!.first.title, 'Weekly commitment');
      }
    });

    test('getWeeklyPlans handles API failures', () async {
      final mockClient = MockStrategyMvpClient();
      mockClient.setListTwelveWeekPlansResult(
        Future.value(
          ApiFailure<List<MvpWeeklyPlan>>(
            _failureDetail(ApiFailureCode.unavailable),
          ),
        ),
      );

      final service = TwelveWyService(client: mockClient);
      final result = await service.getWeeklyPlans();

      expect(result, isA<ApiFailure>());
    });
  });
}
