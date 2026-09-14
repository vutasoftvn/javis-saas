import 'dart:async';
import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:get/get.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:frontend/core/network/mvp_request_client.dart';
import 'package:frontend/core/services/secure_storage_service.dart';
import 'package:frontend/modules/projects/controllers/project_operating_loop_controller.dart';
import 'package:frontend/modules/projects/services/project_operating_loop_service.dart';
import 'package:frontend/modules/projects/views/widgets/cycle_week_section.dart';

Map<String, dynamic> _envelope(Object? data) => {
      'data': data,
      'meta': {
        'dataState': 'populated',
        'observedAt': '2026-09-10T12:00:00Z',
        'sources': [
          {'kind': 'company_db', 'ref': 'operating'},
        ],
      },
    };

Map<String, dynamic> _cycleJson({int currentWeek = 3, String status = 'ACTIVE'}) => {
      'id': 'cycle_1',
      'workspaceId': '1001',
      'projectId': '42',
      'currentWeek': currentWeek,
      'durationWeeks': 6,
      'theme': null,
      'visionStatement': 'Grow',
      'status': status,
      'timezone': 'UTC',
      'startLocalDate': null,
      'startDate': '2026-08-01',
      'endDate': null,
      'createdAt': '2026-09-10T12:00:00Z',
      'updatedAt': '2026-09-10T12:00:00Z',
      'sourceObjectiveId': null,
    };

Map<String, dynamic> _weekJson({int weekNo = 3}) => {
      'id': 'week_$weekNo',
      'workspaceId': '1001',
      'projectId': '42',
      'cycleId': 'cycle_1',
      'weekNo': weekNo,
      'focus': 'Focus $weekNo',
      'mission': null,
      'executionScore': null,
      'outcomeScore': null,
      'reflection': null,
      'startDate': null,
      'endDate': null,
      'createdAt': '2026-09-10T12:00:00Z',
      'updatedAt': '2026-09-10T12:00:00Z',
    };

Map<String, dynamic> _loopJson({int currentWeek = 3, String status = 'ACTIVE'}) => {
      'project': {
        'id': '42',
        'workspaceId': '1001',
        'title': 'Test Project',
        'lifecycleStage': 'P0_DISCOVERY',
        'stageVersion': 1,
        'status': 'ACTIVE',
        'createdAt': '2026-09-10T12:00:00Z',
      },
      'activeCycle': _cycleJson(currentWeek: currentWeek, status: status),
      'currentWeek': _weekJson(weekNo: currentWeek),
      'commitments': <dynamic>[],
      'objectives': <dynamic>[],
      'tasks': <dynamic>[],
    };

/// Harness giống `ProjectOperatingLoopView` thật: bọc `CycleWeekSection`
/// trong `Obx` đọc `controller.loop.value` để test đúng hành vi
/// "chỉ hiện tuần mới SAU KHI reload xong", không phải optimistic update.
Widget _harness(ProjectOperatingLoopController controller) {
  return GetMaterialApp(
    home: Scaffold(
      body: Obx(() {
        final loop = controller.loop.value;
        return CycleWeekSection(
          controller: controller,
          activeCycle: loop?.activeCycle,
          currentWeek: loop?.currentWeek,
        );
      }),
    ),
  );
}

void main() {
  setUp(() async {
    Get.testMode = true;
    SharedPreferences.setMockInitialValues({'workspace_id': '1001'});
    await SecureStorageService.write('auth_token', 'test-token');
  });

  tearDown(() {
    Get.reset();
  });

  testWidgets('close week button hidden when cycle is completed', (tester) async {
    final mockHttp = MockClient((request) async {
      return http.Response(
        jsonEncode(_envelope(_loopJson(currentWeek: 6, status: 'COMPLETED'))),
        200,
        headers: {'content-type': 'application/json'},
      );
    });
    final controller = ProjectOperatingLoopController(
      projectId: '42',
      service: ProjectOperatingLoopService(client: MvpRequestClient(httpClient: mockHttp)),
    );
    await controller.loadLoop();

    await tester.pumpWidget(_harness(controller));
    await tester.pumpAndSettle();

    expect(find.byKey(const Key('close_week_button')), findsNothing);
    expect(find.text('Status: COMPLETED'), findsOneWidget);
  });

  testWidgets('close week opens dialog requiring non-empty reflection', (tester) async {
    final mockHttp = MockClient((request) async {
      return http.Response(
        jsonEncode(_envelope(_loopJson())),
        200,
        headers: {'content-type': 'application/json'},
      );
    });
    final controller = ProjectOperatingLoopController(
      projectId: '42',
      service: ProjectOperatingLoopService(client: MvpRequestClient(httpClient: mockHttp)),
    );
    await controller.loadLoop();

    await tester.pumpWidget(_harness(controller));
    await tester.pumpAndSettle();

    expect(find.byKey(const Key('close_week_button')), findsOneWidget);
    await tester.tap(find.byKey(const Key('close_week_button')));
    await tester.pumpAndSettle();

    expect(find.byKey(const Key('close_week_reflection_field')), findsOneWidget);
    final submitButtonFinder = find.byKey(const Key('close_week_submit_button'));
    var submitButton = tester.widget<ElevatedButton>(submitButtonFinder);
    expect(submitButton.onPressed, isNull, reason: 'empty reflection must block submit');

    await tester.enterText(find.byKey(const Key('close_week_reflection_field')), 'Shipped v1');
    await tester.pump();

    submitButton = tester.widget<ElevatedButton>(submitButtonFinder);
    expect(submitButton.onPressed, isNotNull, reason: 'non-empty reflection enables submit');
  });

  testWidgets(
    'submit sends exact expectedCurrentWeek, disables button while in-flight, '
    'and shows next week only after reload completes',
    (tester) async {
      final loadCompleter = Completer<void>();
      var patchCount = 0;
      var loadCount = 0;
      Map<String, dynamic>? capturedBody;
      String? patchedPath;

      final mockHttp = MockClient((request) async {
        if (request.method == 'PATCH') {
          patchCount++;
          patchedPath = request.url.path;
          capturedBody = jsonDecode(request.body) as Map<String, dynamic>;
          return http.Response(
            jsonEncode(_envelope(null)),
            200,
            headers: {'content-type': 'application/json'},
          );
        }
        loadCount++;
        if (loadCount == 1) {
          // Initial loadLoop() called from controller construction path.
          return http.Response(
            jsonEncode(_envelope(_loopJson(currentWeek: 3))),
            200,
            headers: {'content-type': 'application/json'},
          );
        }
        // Reload triggered by closeCurrentWeek() — delayed so the test can
        // assert the submit button is disabled and the UI still shows week 3
        // while this request is in flight.
        await loadCompleter.future;
        return http.Response(
          jsonEncode(_envelope(_loopJson(currentWeek: 4))),
          200,
          headers: {'content-type': 'application/json'},
        );
      });

      final controller = ProjectOperatingLoopController(
        projectId: '42',
        service: ProjectOperatingLoopService(client: MvpRequestClient(httpClient: mockHttp)),
      );
      await controller.loadLoop();

      await tester.pumpWidget(_harness(controller));
      await tester.pumpAndSettle();

      await tester.tap(find.byKey(const Key('close_week_button')));
      await tester.pumpAndSettle();
      await tester.enterText(find.byKey(const Key('close_week_reflection_field')), 'Shipped v1');
      await tester.pump();

      await tester.tap(find.byKey(const Key('close_week_submit_button')));
      await tester.pump(); // starts the async submit, reload is now pending

      // While the reload is still in flight: submit button must be disabled
      // and the UI must still show the OLD week (no optimistic update).
      final submitButton =
          tester.widget<ElevatedButton>(find.byKey(const Key('close_week_submit_button')));
      expect(submitButton.onPressed, isNull, reason: 'must disable while submitting');
      expect(find.text('Week 3: Focus 3'), findsOneWidget);
      expect(find.textContaining('Week 4'), findsNothing);

      expect(patchCount, 1);
      expect(patchedPath, '/operations/projects/42/operating-loop/cycles/cycle_1/week');
      expect(capturedBody?['expectedCurrentWeek'], 3, reason: 'must send the real loaded currentWeek');
      expect(capturedBody?['reflection'], 'Shipped v1');

      // Now let the reload finish.
      loadCompleter.complete();
      await tester.pumpAndSettle();

      expect(find.textContaining('Week 4'), findsOneWidget);
      expect(find.byKey(const Key('close_week_reflection_field')), findsNothing,
          reason: 'dialog should be closed after a successful close');
    },
  );

  testWidgets('conflict shows server error in dialog and reloads current state', (tester) async {
    var loadCount = 0;
    final mockHttp = MockClient((request) async {
      if (request.method == 'PATCH') {
        return http.Response(
          jsonEncode({'message': 'expectedCurrentWeek is stale'}),
          409,
          headers: {'content-type': 'application/json'},
        );
      }
      loadCount++;
      return http.Response(
        jsonEncode(_envelope(_loopJson(currentWeek: 3))),
        200,
        headers: {'content-type': 'application/json'},
      );
    });
    final controller = ProjectOperatingLoopController(
      projectId: '42',
      service: ProjectOperatingLoopService(client: MvpRequestClient(httpClient: mockHttp)),
    );
    await controller.loadLoop();
    expect(loadCount, 1);

    await tester.pumpWidget(_harness(controller));
    await tester.pumpAndSettle();

    await tester.tap(find.byKey(const Key('close_week_button')));
    await tester.pumpAndSettle();
    await tester.enterText(find.byKey(const Key('close_week_reflection_field')), 'Shipped v1');
    await tester.pump();
    await tester.tap(find.byKey(const Key('close_week_submit_button')));
    await tester.pumpAndSettle();

    expect(find.text('expectedCurrentWeek is stale'), findsOneWidget);
    expect(loadCount, 2, reason: 'conflict must still trigger a reload of current state');
    // Dialog stays open (no silent retry with a new version) — the reflection
    // field must still be present, not auto-resubmitted.
    expect(find.byKey(const Key('close_week_reflection_field')), findsOneWidget);
  });
}
