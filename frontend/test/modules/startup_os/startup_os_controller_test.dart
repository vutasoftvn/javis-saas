import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/core/network/api_result.dart';
import 'package:frontend/modules/startup_os/controllers/startup_os_controller.dart';
import 'package:frontend/modules/startup_os/models/startup_os_models.dart';
import 'package:frontend/modules/startup_os/services/startup_os_service.dart';
import 'package:frontend/modules/startup_os/widgets/onboard_wizard_dialog.dart';
import 'package:frontend/modules/startup_os/widgets/startup_os_panel.dart';
import 'package:get/get.dart';

final _meta = ApiResponseMeta(
  dataState: ApiDataState.populated,
  observedAt: DateTime.utc(2026, 9, 26),
);

ApiSuccess<T> _ok<T>(T data) => ApiSuccess(data: data, meta: _meta);

const _failure = ApiFailureDetail(
  code: ApiFailureCode.invalidRequest,
  statusCode: 400,
  message: 'bad field',
);

DimensionCadence _cadence(
  String dim, {
  String cadence = 'fast',
  bool never = false,
  String urgency = 'ok',
}) => DimensionCadence(
  dimension: dim,
  cadence: cadence,
  intervalDays: 14,
  lastReviewedAt: never ? null : '2026-09-20T00:00:00.000Z',
  daysSinceLastReview: never ? null : 6,
  neverReviewed: never,
  urgency: never ? 'critical' : urgency,
);

GoalNode _goal(String id, String title) => GoalNode(
  id: id,
  parentId: null,
  title: title,
  description: null,
  goalType: GoalType.strategic,
  status: 'active',
  startDate: null,
  endDate: null,
  depth: 0,
  objectiveCount: 0,
  krTotal: 4,
  krAchieved: 1,
  children: const [],
);

class FakeStartupOsService extends StartupOsService {
  FakeStartupOsService();

  ApiResult<List<GoalNode>> tree = _ok([]);
  ApiResult<List<DimensionCadence>> cadences = _ok([]);
  ApiResult<List<GoalNeedingReview>> review = _ok([]);
  ApiResult<List<PendingProject>> projects = _ok([]);
  final Set<String> failingDimensions = {};
  final List<String> calls = [];
  final Map<String, Map<String, Object>> updates = {};

  @override
  Future<ApiResult<List<GoalNode>>> getGoalTree() async => tree;
  @override
  Future<ApiResult<List<DimensionCadence>>> getCadenceStatus() async =>
      cadences;
  @override
  Future<ApiResult<List<GoalNeedingReview>>> getGoalsNeedingReview() async =>
      review;
  @override
  Future<ApiResult<List<PendingProject>>> listPendingProjects() async =>
      projects;
  @override
  Future<ApiResult<Map<String, dynamic>>> getCompanyContext() async => _ok({
    'stage_scale': {'stage': 'pre_pmf', 'headcountFt': 3},
    'challenges': null,
  });

  ApiResult<CreatedGoal>? createResult;
  final List<Map<String, Object?>> createCalls = [];
  final List<String> triageCalls = [];

  @override
  Future<ApiResult<CreatedGoal>> createGoal({
    required String title,
    required GoalType goalType,
    String? parentId,
    String? description,
    String? startDate,
    String? endDate,
  }) async {
    createCalls.add({
      'title': title,
      'goalType': goalType,
      'parentId': parentId,
    });
    return createResult ??
        _ok(const CreatedGoal(goalId: '900', cadenceWarnings: []));
  }

  @override
  Future<ApiResult<void>> triageProject({
    required String projectId,
    required TriageAction action,
    String? newGoalId,
    String? newObjectiveTitle,
  }) async {
    triageCalls.add('$projectId:${action.wire}:$newGoalId:$newObjectiveTitle');
    projects = _ok(const []);
    return _ok(null);
  }

  @override
  Future<ApiResult<String>> startSession({
    required String sessionType,
    String? summary,
  }) async {
    calls.add('session:$sessionType');
    return _ok('s1');
  }

  @override
  Future<ApiResult<void>> updateDimension({
    required String sessionId,
    required String dimension,
    required Map<String, Object> data,
  }) async {
    calls.add('dimension:$dimension');
    if (failingDimensions.contains(dimension)) {
      return const ApiFailure(_failure);
    }
    updates[dimension] = data;
    return _ok(null);
  }

  @override
  Future<ApiResult<String>> createSnapshot({
    required String sessionId,
    required List<String> changedDimensions,
    String? changeReason,
  }) async {
    calls.add('snapshot:${changedDimensions.join(',')}');
    return _ok('snap-1');
  }
}

void main() {
  setUp(Get.reset);

  group('StartupOsController', () {
    test('keeps previously loaded data when a refresh fails', () async {
      final service = FakeStartupOsService()
        ..tree = _ok([_goal('1', 'Tầm nhìn')]);
      final controller = StartupOsController(service: service);
      await controller.loadAll();
      expect(controller.goalTree.single.title, 'Tầm nhìn');

      service.tree = const ApiFailure(
        ApiFailureDetail(code: ApiFailureCode.unavailable, message: 'down'),
      );
      await controller.loadAll();
      expect(controller.goalTree.single.title, 'Tầm nhìn');
      expect(controller.treeError.value?.code, ApiFailureCode.unavailable);
    });

    test('flags stale fast dimensions only', () async {
      final service = FakeStartupOsService()
        ..cadences = _ok([
          _cadence('stage_scale', never: true),
          _cadence('challenges'),
          _cadence('identity', cadence: 'slow', never: true),
        ]);
      final controller = StartupOsController(service: service);
      await controller.loadAll();
      expect(controller.staleFastDimensions.map((c) => c.dimension), [
        'stage_scale',
      ]);
    });

    test('submits dimensions then snapshots only what was saved', () async {
      final service = FakeStartupOsService();
      final controller = StartupOsController(service: service);
      final outcome = await controller.submitOnboarding(
        fullSetup: false,
        payloads: {
          'stage_scale': {'stage': 'pre_pmf'},
          'challenges': {'priorityMoney': 5},
        },
      );
      expect(outcome, isA<OnboardSubmitted>());
      expect(service.calls, [
        'session:partial_update',
        'dimension:stage_scale',
        'dimension:challenges',
        'snapshot:stage_scale,challenges',
      ]);
    });

    test(
      'stops at the first failing dimension and reports what was already saved',
      () async {
        final service = FakeStartupOsService()
          ..failingDimensions.add('challenges');
        final controller = StartupOsController(service: service);
        final outcome = await controller.submitOnboarding(
          fullSetup: true,
          payloads: {
            'stage_scale': {'stage': 'pre_pmf'},
            'challenges': {'priorityMoney': 5},
            'identity': {'whatTheyDo': 'x'},
          },
        );
        expect(outcome, isA<OnboardSubmitFailed>());
        final failed = outcome as OnboardSubmitFailed;
        expect(failed.savedDimensions, ['stage_scale']);
        expect(failed.failedDimension, 'challenges');
        expect(service.calls.any((c) => c.startsWith('snapshot')), isFalse);
        expect(service.calls.contains('dimension:identity'), isFalse);
      },
    );
  });

  group('Startup OS widgets', () {
    // Chạy mỗi widget test ở khổ điện thoại và desktop (logical px, DPR 1).
    const sizes = {'phone': Size(390, 844), 'desktop': Size(1400, 1000)};
    void useSize(WidgetTester tester, Size size) {
      tester.view.devicePixelRatio = 1.0;
      tester.view.physicalSize = size;
      addTearDown(tester.view.reset);
    }

    Future<StartupOsController> pumpPanel(
      WidgetTester tester,
      FakeStartupOsService service,
    ) async {
      final controller = Get.put(StartupOsController(service: service));
      await tester.pumpWidget(
        const GetMaterialApp(home: Scaffold(body: StartupOsPanel())),
      );
      await tester.pumpAndSettle();
      return controller;
    }

    for (final MapEntry(key: label, value: size) in sizes.entries) {
      testWidgets(
        'shows freshness chips, review badge and goal progress [$label]',
        (tester) async {
          useSize(tester, size);
          final service = FakeStartupOsService()
            ..cadences = _ok([
              _cadence('stage_scale', never: true),
              _cadence('challenges'),
            ])
            ..review = _ok([
              GoalNeedingReview(
                goalId: '1',
                goalTitle: 'Tầm nhìn',
                goalType: 'strategic',
                snapshotAgeDays: 40,
                urgency: 'high',
              ),
            ])
            ..tree = _ok([_goal('1', 'Tầm nhìn')]);
          await pumpPanel(tester, service);

          expect(
            find.text('Giai đoạn & Quy mô · Chưa ghi nhận'),
            findsOneWidget,
          );
          expect(
            find.byKey(const Key('goals-needing-review-badge')),
            findsOneWidget,
          );
          expect(find.text('Tầm nhìn'), findsOneWidget);
          expect(find.text('1/4 KR'), findsOneWidget);
        },
      );
    }

    for (final MapEntry(key: label, value: size) in sizes.entries) {
      testWidgets(
        'asks to refresh stale fast context before creating a goal [$label]',
        (tester) async {
          useSize(tester, size);
          final service = FakeStartupOsService()
            ..cadences = _ok([_cadence('stage_scale', never: true)]);
          await pumpPanel(tester, service);

          await tester.tap(find.byKey(const Key('add-goal-button')));
          await tester.pumpAndSettle();
          expect(find.text('Ngữ cảnh chưa cập nhật'), findsOneWidget);
          expect(find.text('Cập nhật nhanh trước'), findsOneWidget);
        },
      );
    }

    for (final MapEntry(key: label, value: size) in sizes.entries) {
      testWidgets(
        'wizard only submits dimensions the founder edited or confirmed [$label]',
        (tester) async {
          useSize(tester, size);
          final service = FakeStartupOsService();
          final controller = StartupOsController(service: service);
          OnboardSubmitOutcome? outcome;
          await tester.pumpWidget(
            GetMaterialApp(
              home: Builder(
                builder: (context) => Scaffold(
                  body: TextButton(
                    onPressed: () async {
                      outcome = await showDialog<OnboardSubmitOutcome>(
                        context: context,
                        builder: (_) => OnboardWizardDialog(
                          controller: controller,
                          fullSetup: false,
                        ),
                      );
                    },
                    child: const Text('open'),
                  ),
                ),
              ),
            ),
          );
          await tester.tap(find.text('open'));
          await tester.pumpAndSettle();

          // stage_scale được điền sẵn từ ngữ cảnh nhưng Founder chưa xác nhận.
          final headcount = find.byKey(
            const Key('field-stage_scale-headcountFt'),
          );
          expect(tester.widget<TextField>(headcount).controller!.text, '3');
          await tester.tap(find.byKey(const Key('wizard-submit')));
          await tester.pumpAndSettle();
          expect(find.byKey(const Key('wizard-error')), findsOneWidget);
          expect(service.calls, isEmpty);

          await tester.enterText(headcount, '5');
          await tester.tap(find.byKey(const Key('wizard-submit')));
          await tester.pumpAndSettle();

          expect(outcome, isA<OnboardSubmitted>());
          expect(service.calls, [
            'session:partial_update',
            'dimension:stage_scale',
            'snapshot:stage_scale',
          ]);
          expect(service.updates['stage_scale']!['headcountFt'], 5);
          expect(service.updates['stage_scale']!['stage'], 'pre_pmf');
        },
      );
    }
    for (final MapEntry(key: label, value: size) in sizes.entries) {
      testWidgets(
        'create goal keeps the dialog open on failure and closes on success [$label]',
        (tester) async {
          useSize(tester, size);
          final service = FakeStartupOsService()
            ..cadences = _ok([_cadence('stage_scale'), _cadence('challenges')])
            ..createResult = const ApiFailure(_failure);
          await pumpPanel(tester, service);

          await tester.tap(find.byKey(const Key('add-goal-button')));
          await tester.pumpAndSettle();
          await tester.tap(find.byKey(const Key('create-goal-submit')));
          await tester.pumpAndSettle();
          expect(find.byKey(const Key('create-goal-error')), findsOneWidget);
          expect(service.createCalls, isEmpty);

          await tester.enterText(
            find.byKey(const Key('goal-title-field')),
            '100 khách trả tiền',
          );
          await tester.tap(find.byKey(const Key('create-goal-submit')));
          await tester.pumpAndSettle();
          expect(find.byKey(const Key('create-goal-error')), findsOneWidget);
          expect(find.text('Dữ liệu không hợp lệ: bad field'), findsOneWidget);

          service.createResult = null;
          await tester.tap(find.byKey(const Key('create-goal-submit')));
          await tester.pump();
          await tester.pump(const Duration(seconds: 1));
          expect(find.byKey(const Key('create-goal-submit')), findsNothing);
          expect(service.createCalls.length, 2);
          expect(service.createCalls.last['goalType'], GoalType.strategic);
          await tester.pump(const Duration(seconds: 5));
        },
      );
    }

    for (final MapEntry(key: label, value: size) in sizes.entries) {
      testWidgets('triage marks a discovery project as R&D [$label]', (
        tester,
      ) async {
        useSize(tester, size);
        final service = FakeStartupOsService()
          ..projects = _ok(const [
            PendingProject(
              id: '31',
              title: 'Thử kênh TikTok',
              description: null,
              origin: 'discovery',
            ),
          ]);
        await pumpPanel(tester, service);

        await tester.tap(find.byKey(const Key('open-triage-button')));
        await tester.pumpAndSettle();
        await tester.tap(find.text('Quyết định'));
        await tester.pumpAndSettle();
        await tester.tap(find.text(TriageAction.markRd.label).last);
        await tester.pumpAndSettle();
        await tester.tap(find.text('Áp dụng'));
        await tester.pump();
        await tester.pump(const Duration(seconds: 1));
        expect(service.triageCalls, ['31:mark_rd:null:null']);
        await tester.pump(const Duration(seconds: 5));
      });
    }
  });
}
