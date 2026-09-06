import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/core/network/api_client.dart';
import 'package:frontend/modules/strategy/widgets/cycle_review_timeline.dart';
import 'package:frontend/modules/strategy/widgets/initiative_plan_panel.dart';
import 'package:frontend/modules/strategy/widgets/workspace_strategy_settings_sheet.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';

Future<void> _pumpApp(WidgetTester tester, Widget child, {Size size = const Size(1280, 900)}) async {
  tester.view.physicalSize = size;
  tester.view.devicePixelRatio = 1.0;
  addTearDown(() {
    tester.view.resetPhysicalSize();
    tester.view.resetDevicePixelRatio();
  });
  await tester.pumpWidget(
    MaterialApp(
      home: Scaffold(
        body: child,
      ),
    ),
  );
  await tester.pumpAndSettle();
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  late http.Client originalClient;

  setUp(() {
    originalClient = ApiClient.client;
    SharedPreferences.setMockInitialValues({'workspace_id': 'ws-123'});
  });

  tearDown(() {
    ApiClient.client = originalClient;
  });

  group('Task 11: Initiative Planning, Reviews Timeline & Settings Tests', () {
    testWidgets('1. Initiative approval state gates task association until approved', (tester) async {
      // Setup mock backend with 1 DRAFT initiative
      ApiClient.client = MockClient((request) async {
        if (request.url.path == '/operations/initiatives' && request.method == 'GET') {
          return http.Response(
            jsonEncode({
              'initiatives': [
                {
                  'id': 'init-1',
                  'workspaceId': 'ws-123',
                  'title': 'Sáng kiến A (Mở rộng kênh đại lý)',
                  'status': 'active',
                  'approvalStatus': 'DRAFT',
                  'revision': 1,
                  'keyResultIds': ['kr-1'],
                }
              ]
            }),
            200,
            headers: {'content-type': 'application/json; charset=utf-8'},
          );
        }
        if (request.url.path == '/operations/initiatives/init-1/approve' && request.method == 'POST') {
          return http.Response(
            jsonEncode({
              'id': 'init-1',
              'workspaceId': 'ws-123',
              'title': 'Sáng kiến A (Mở rộng kênh đại lý)',
              'status': 'active',
              'approvalStatus': 'APPROVED',
              'approvedByMemberId': 'founder-1',
              'decisionId': 'dec-999',
              'revision': 2,
              'keyResultIds': ['kr-1'],
            }),
            200,
            headers: {'content-type': 'application/json; charset=utf-8'},
          );
        }
        return http.Response('not found', 404);
      });

      await _pumpApp(
        tester,
        const InitiativePlanPanel(
          strategicObjectiveId: 'strat-1',
          availableKrIds: ['kr-1'],
        ),
      );

      // Verify initiative is rendered with DRAFT status badge
      expect(find.text('Sáng kiến A (Mở rộng kênh đại lý)'), findsOneWidget);
      expect(find.text('BẢN NHÁP (DRAFT)'), findsOneWidget);

      // Try associating task with unapproved initiative
      await tester.enterText(
        find.byKey(const ValueKey('weekly_task_title_input')),
        'Soạn hợp đồng đại lý mẫu',
      );
      await tester.pumpAndSettle();

      // Open dropdown and pick the draft initiative
      await tester.tap(find.byKey(const ValueKey('task_initiative_dropdown')));
      await tester.pumpAndSettle();

      await tester.tap(find.textContaining('Sáng kiến A').last);
      await tester.pumpAndSettle();

      // Tap assign task button
      await tester.tap(find.byKey(const ValueKey('assign_task_button')));
      await tester.pumpAndSettle();

      // Must be blocked with error message
      expect(find.byKey(const ValueKey('task_assignment_error_message')), findsOneWidget);
      expect(find.textContaining('chưa được phê duyệt (Approval: DRAFT)'), findsOneWidget);

      // Now approve the initiative
      final approveBtn = find.byKey(const ValueKey('approve_initiative_button_init-1'));
      expect(approveBtn, findsOneWidget);
      await tester.tap(approveBtn);
      await tester.pumpAndSettle();

      // Verify status changed to APPROVED
      expect(find.text('ĐÃ DUYỆT (APPROVED)'), findsOneWidget);

      // Now try adding task again
      await tester.tap(find.byKey(const ValueKey('assign_task_button')));
      await tester.pumpAndSettle();

      // Error message should be gone and task should be attached
      expect(find.byKey(const ValueKey('task_assignment_error_message')), findsNothing);
      expect(find.text('Soạn hợp đồng đại lý mẫu'), findsOneWidget);
      expect(find.text('Gắn sáng kiến'), findsOneWidget);
    });

    testWidgets('2. BAU task creation allows unlinked tasks without initiative', (tester) async {
      ApiClient.client = MockClient((request) async {
        if (request.url.path == '/operations/initiatives') {
          return http.Response(
            jsonEncode({'initiatives': []}),
            200,
            headers: {'content-type': 'application/json; charset=utf-8'},
          );
        }
        return http.Response('not found', 404);
      });

      await _pumpApp(
        tester,
        const InitiativePlanPanel(
          strategicObjectiveId: 'strat-1',
        ),
      );

      // Enter task title
      await tester.enterText(
        find.byKey(const ValueKey('weekly_task_title_input')),
        'Họp giao ban định kỳ thứ 2',
      );
      await tester.pumpAndSettle();

      // Check BAU checkbox
      await tester.tap(find.byKey(const ValueKey('bau_task_checkbox')));
      await tester.pumpAndSettle();

      // Tap assign task button
      await tester.tap(find.byKey(const ValueKey('assign_task_button')));
      await tester.pumpAndSettle();

      // Task is added under BAU section
      expect(find.text('Họp giao ban định kỳ thứ 2'), findsOneWidget);
      expect(find.text('BAU'), findsOneWidget);
      expect(find.byKey(const ValueKey('task_assignment_error_message')), findsNothing);
    });

    testWidgets('3. One- and two-option policies are configured and constrained', (tester) async {
      Map<String, dynamic> lastPutBody = {};

      ApiClient.client = MockClient((request) async {
        if (request.url.path == '/operations/strategy/settings') {
          if (request.method == 'GET') {
            return http.Response(
              jsonEncode({
                'settings': {
                  'workspaceId': 'ws-123',
                  'strategyMethod': 'BSC_FILTER',
                  'bscMode': 'REQUIRED',
                  'enabledBscPerspectives': ['FINANCIAL', 'CUSTOMER'],
                  'towsSelectionLimit': 1,
                  'weeklyReviewEnabled': true,
                  'midCycleReviewPolicy': 'AUTO',
                  'endCycleReviewEnabled': true,
                  'allowedAgentProfiles': ['strategic_copilot'],
                  'approvalPolicy': 'FOUNDER_ONLY',
                  'revision': 1,
                },
                'canEdit': true,
              }),
              200,
              headers: {'content-type': 'application/json; charset=utf-8'},
            );
          }
          if (request.method == 'PUT') {
            lastPutBody = jsonDecode(request.body);
            return http.Response(
              jsonEncode({
                'settings': {
                  ...lastPutBody,
                  'workspaceId': 'ws-123',
                  'revision': 2,
                },
                'canEdit': true,
              }),
              200,
              headers: {'content-type': 'application/json; charset=utf-8'},
            );
          }
        }
        return http.Response('not found', 404);
      });

      await _pumpApp(
        tester,
        const WorkspaceStrategySettingsSheet(),
      );

      // Verify initial limit is 1 option
      expect(find.text('1 chiến lược trọng tâm (Tập trung tối đa)'), findsOneWidget);

      // Change limit to 2 options
      await tester.tap(find.byKey(const ValueKey('settings_tows_limit_dropdown')));
      await tester.pumpAndSettle();

      await tester.tap(find.text('2 chiến lược song song').last);
      await tester.pumpAndSettle();

      // Save changes
      await tester.tap(find.byKey(const ValueKey('settings_save_button')));
      await tester.pumpAndSettle();

      // Verify payload sent to server has towsSelectionLimit == 2
      expect(lastPutBody['towsSelectionLimit'], 2);
    });

    testWidgets('4. 10-week cycle positions Mid-cycle review at Week 5 with server permission gating', (tester) async {
      final reviews = [
        {
          'id': 'rev-w1',
          'workspaceId': 'ws-123',
          'cycleId': 'cycle-10w',
          'kind': 'WEEKLY',
          'scheduledWeekNo': 1,
          'status': 'COMPLETED',
          'settingsRevision': 1,
          'revision': 1,
          'canEdit': false,
          'canClose': false,
        },
        {
          'id': 'rev-mid5',
          'workspaceId': 'ws-123',
          'cycleId': 'cycle-10w',
          'kind': 'MID_CYCLE',
          'scheduledWeekNo': 5,
          'status': 'IN_PROGRESS',
          'settingsRevision': 1,
          'decisionId': 'dec-mid-5',
          'revision': 2,
          'canEdit': true,
          'canClose': true,
        },
        {
          'id': 'rev-end10',
          'workspaceId': 'ws-123',
          'cycleId': 'cycle-10w',
          'kind': 'END_CYCLE',
          'scheduledWeekNo': 10,
          'status': 'SCHEDULED',
          'settingsRevision': 1,
          'revision': 1,
          'canEdit': true,
          'canClose': false,
        },
      ];

      ApiClient.client = MockClient((request) async {
        if (request.url.path == '/operations/cycles/cycle-10w/reviews') {
          return http.Response(
            jsonEncode({'reviews': reviews}),
            200,
            headers: {'content-type': 'application/json; charset=utf-8'},
          );
        }
        if (request.url.path == '/operations/cycle-reviews/rev-mid5/close') {
          return http.Response(
            jsonEncode({
              'id': 'rev-mid5',
              'workspaceId': 'ws-123',
              'cycleId': 'cycle-10w',
              'kind': 'MID_CYCLE',
              'scheduledWeekNo': 5,
              'status': 'COMPLETED',
              'conclusion': 'Đạt 80% chỉ tiêu giữa chu kỳ',
              'settingsRevision': 1,
              'decisionId': 'dec-mid-5',
              'revision': 3,
            }),
            200,
            headers: {'content-type': 'application/json; charset=utf-8'},
          );
        }
        return http.Response('not found', 404);
      });

      await _pumpApp(
        tester,
        const CycleReviewTimeline(
          cycleId: 'cycle-10w',
          cycleDurationWeeks: 10,
        ),
      );

      // Verify mid-cycle review is at week 5
      expect(find.textContaining('giữa chu kỳ'), findsOneWidget);
      expect(find.byKey(const ValueKey('review_week_rev-mid5')), findsOneWidget);
      expect(find.text('Tuần 5'), findsOneWidget);
      expect(find.byKey(const ValueKey('review_decision_link_rev-mid5')), findsOneWidget);
      expect(find.text('Biên bản quyết định #dec-mid-5'), findsOneWidget);

      // Verify close button is present because canClose == true
      final closeBtn = find.byKey(const ValueKey('close_review_button_rev-mid5'));
      expect(closeBtn, findsOneWidget);

      // Tap close review
      await tester.tap(closeBtn);
      await tester.pumpAndSettle();

      // Enter conclusion in dialog
      await tester.enterText(
        find.byKey(const ValueKey('review_conclusion_input')),
        'Đạt 80% chỉ tiêu giữa chu kỳ',
      );
      await tester.pumpAndSettle();

      // Confirm close
      await tester.tap(find.byKey(const ValueKey('confirm_close_review_button')));
      await tester.pumpAndSettle();

      // Verify status updated to completed
      expect(find.text('HOÀN THÀNH'), findsNWidgets(2)); // Week 1 + Mid-cycle
    });

    testWidgets('5. Settings sheet enters read-only state when canEdit is false', (tester) async {
      ApiClient.client = MockClient((request) async {
        if (request.url.path == '/operations/strategy/settings') {
          return http.Response(
            jsonEncode({
              'settings': {
                'workspaceId': 'ws-123',
                'strategyMethod': 'CLASSIC',
                'bscMode': 'OPTIONAL',
                'enabledBscPerspectives': ['FINANCIAL'],
                'towsSelectionLimit': 1,
                'weeklyReviewEnabled': false,
                'midCycleReviewPolicy': 'OFF',
                'endCycleReviewEnabled': true,
                'allowedAgentProfiles': [],
                'approvalPolicy': 'FOUNDER_ONLY',
                'revision': 1,
              },
              'canEdit': false, // Read-only!
            }),
            200,
            headers: {'content-type': 'application/json; charset=utf-8'},
          );
        }
        return http.Response('not found', 404);
      });

      await _pumpApp(
        tester,
        const WorkspaceStrategySettingsSheet(),
      );

      // Verify read-only notice is displayed
      expect(find.byKey(const ValueKey('settings_read_only_banner')), findsOneWidget);
      expect(find.textContaining('Chế độ chỉ đọc: Bạn không có quyền'), findsOneWidget);

      // Save button is disabled (onPressed is null)
      final saveBtn = tester.widget<ElevatedButton>(find.byKey(const ValueKey('settings_save_button')));
      expect(saveBtn.onPressed, isNull);
    });

    testWidgets('6. Settings sheet recovers from 409 revision conflict by reloading', (tester) async {
      int getCalls = 0;

      ApiClient.client = MockClient((request) async {
        if (request.url.path == '/operations/strategy/settings') {
          if (request.method == 'GET') {
            getCalls++;
            final rev = getCalls == 1 ? 1 : 2;
            return http.Response(
              jsonEncode({
                'settings': {
                  'workspaceId': 'ws-123',
                  'strategyMethod': 'BSC_FILTER',
                  'bscMode': 'REQUIRED',
                  'enabledBscPerspectives': ['FINANCIAL'],
                  'towsSelectionLimit': rev == 1 ? 1 : 2,
                  'weeklyReviewEnabled': true,
                  'midCycleReviewPolicy': 'AUTO',
                  'endCycleReviewEnabled': true,
                  'allowedAgentProfiles': [],
                  'approvalPolicy': 'FOUNDER_ONLY',
                  'revision': rev,
                },
                'canEdit': true,
              }),
              200,
              headers: {'content-type': 'application/json; charset=utf-8'},
            );
          }
          if (request.method == 'PUT') {
            // Emulate 409 revision conflict
            return http.Response(
              jsonEncode({
                'message': 'Settings revision conflict. Expected 1 but was 2.',
                'currentRevision': 2,
              }),
              409,
              headers: {'content-type': 'application/json; charset=utf-8'},
            );
          }
        }
        return http.Response('not found', 404);
      });

      await _pumpApp(
        tester,
        const WorkspaceStrategySettingsSheet(),
      );

      expect(getCalls, 1);
      expect(find.text('1 chiến lược trọng tâm (Tập trung tối đa)'), findsOneWidget);

      // Attempt to save
      await tester.tap(find.byKey(const ValueKey('settings_save_button')));
      await tester.pumpAndSettle();

      // Must catch 409, show conflict recovery banner, and call GET again
      expect(getCalls, 2);
      expect(find.byKey(const ValueKey('settings_conflict_banner')), findsOneWidget);
      expect(find.textContaining('Xung đột phiên bản (409)'), findsOneWidget);

      // Fresh data (limit 2, rev 2) is loaded and displayed
      expect(find.text('2 chiến lược song song'), findsOneWidget);
    });
  });
}
