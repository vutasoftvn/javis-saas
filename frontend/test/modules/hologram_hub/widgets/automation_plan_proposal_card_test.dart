import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:get/get.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:frontend/core/network/api_client.dart';
import 'package:frontend/core/routing/app_routes.dart';
import 'package:frontend/core/ui/app_copy.dart';
import 'package:frontend/modules/hologram_hub/controllers/founder_command_center_controller.dart';
import 'package:frontend/modules/hologram_hub/controllers/hub_operations_controller.dart';
import 'package:frontend/modules/hologram_hub/widgets/chat_panel_content.dart';

// Task 7 (B6) — thẻ đề xuất kế hoạch tự động hoá trong chat. Message model tự in
// `{"kind":"automation_plan_proposal",...}` làm content (cùng cơ chế parse-JSON-làm-content
// với `plan_progress`/`memory_confirm` — không phải SSE event riêng, xem task-7-brief.md).
// Shape dựa theo task-5-report.md mục ROUTE (§1 200 response).

String _readyProposalJson({String proposalId = 'prop_1'}) => jsonEncode({
      'kind': 'automation_plan_proposal',
      'proposalId': proposalId,
      'projectId': 'p1',
      'status': 'DRAFT',
      'plan': {
        'agentDeploymentId': 'dep_1',
        'agentLabel': 'AI operations',
        'proposeNewAgent': false,
        'skillId': 'operations.email-digest',
        'skillLabel': 'Tóm tắt email chưa đọc',
        'connectors': [
          {'key': 'email-read', 'status': 'connected'},
        ],
        'channel': {'kind': 'telegram', 'label': 'Founder | Telegram', 'verified': true},
        'schedule': {
          'kind': 'daily',
          'timezone': 'Asia/Ho_Chi_Minh',
          'hour': 7,
          'minute': 30,
          'weekdays': [],
          'runAt': null,
          'humanReadable': 'Hằng ngày lúc 07:30 (Asia/Ho_Chi_Minh)',
        },
        'tokenBudgetPerRun': 20000,
        'capabilityIds': ['email.digest.read', 'founder.notify.send'],
      },
      'readiness': {'ready': true, 'blockers': <Object?>[]},
      'createdAt': '2026-09-28T00:00:00Z',
      'decidedAt': null,
      'approvedScheduleId': null,
    });

Map<String, dynamic> _blockedPlan({required List<Map<String, String>> blockers}) => {
      'kind': 'automation_plan_proposal',
      'proposalId': 'prop_2',
      'projectId': 'p1',
      'status': 'DRAFT',
      'plan': {
        'agentDeploymentId': null,
        'agentLabel': 'AI operations',
        'proposeNewAgent': true,
        'skillId': 'operations.email-digest',
        'skillLabel': 'Tóm tắt email chưa đọc',
        'connectors': [
          {'key': 'email-read', 'status': 'missing'},
        ],
        'channel': {'kind': 'telegram', 'label': 'Founder | Telegram', 'verified': false},
        'schedule': {
          'kind': 'daily',
          'timezone': 'Asia/Ho_Chi_Minh',
          'hour': 7,
          'minute': 30,
          'weekdays': [],
          'runAt': null,
          'humanReadable': 'Hằng ngày lúc 07:30 (Asia/Ho_Chi_Minh)',
        },
        'tokenBudgetPerRun': 20000,
        'capabilityIds': ['email.digest.read', 'founder.notify.send'],
      },
      'readiness': {'ready': false, 'blockers': blockers},
      'createdAt': '2026-09-28T00:00:00Z',
      'decidedAt': null,
      'approvedScheduleId': null,
    };

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  late http.Client realClient;

  setUp(() {
    Get.reset();
    Get.testMode = true;
    realClient = ApiClient.client;
    SharedPreferences.setMockInitialValues({'workspace_id': 'ws_1'});
  });

  tearDown(() {
    ApiClient.client = realClient;
  });

  Future<void> pumpChat(
    WidgetTester tester,
    FounderCommandCenterController controller, {
    NavigatorObserver? observer,
  }) async {
    await tester.pumpWidget(
      GetMaterialApp(
        navigatorObservers: observer != null ? [observer] : const [],
        getPages: [
          GetPage(name: AppRoutes.profile, page: () => const Scaffold(body: Text('Profile'))),
        ],
        home: Scaffold(
          body: ChatPanelContent(controller: controller, onClose: () {}),
        ),
      ),
    );
    await tester.pump();
  }

  testWidgets('readiness.ready=true: approve button enabled, calls approve API, shows success',
      (tester) async {
    final requests = <String>[];
    Map<String, dynamic>? approveBody;
    ApiClient.client = MockClient((request) async {
      requests.add('${request.method} ${request.url.path}');
      // Controller nạp nền (workforce packs/approvals) cũng đi qua `ApiClient.client` chung —
      // chỉ khớp cứng đúng request approve, các request khác trả 404 rỗng (không ảnh hưởng
      // assertion của thẻ, controller đã tự xử lý lỗi 404 nền đó).
      if (request.url.path == '/cosa/workspaces/ws_1/automation-plans/prop_1/approve') {
        approveBody = jsonDecode(request.body) as Map<String, dynamic>;
        return http.Response(
          jsonEncode({
            'id': 'sched_1',
            'scheduleKind': 'daily',
            'timezone': 'Asia/Ho_Chi_Minh',
            'hour': 7,
            'minute': 30,
            'state': 'enabled',
          }),
          200,
          headers: {'content-type': 'application/json'},
        );
      }
      return http.Response('{"code":"not_found"}', 404);
    });

    final controller = Get.put(FounderCommandCenterController());
    controller.chatMessages.add({'role': 'assistant', 'content': _readyProposalJson()});
    await pumpChat(tester, controller);

    final approveButton = find.byKey(const Key('automation_plan_approve_button'));
    expect(approveButton, findsOneWidget);
    expect(tester.widget<FilledButton>(approveButton).onPressed, isNotNull);

    await tester.tap(approveButton);
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 50));

    expect(requests, contains('POST /cosa/workspaces/ws_1/automation-plans/prop_1/approve'));
    expect(approveBody, {'projectId': 'p1'});
    expect(find.textContaining(AppCopy.automationPlanApproved), findsOneWidget);
    expect(find.byKey(const Key('automation_plan_approve_button')), findsNothing);
  });

  testWidgets(
      'readiness.ready=false with 1 blocker: approve disabled, correct secondary button, '
      'tools_tab signals real controller call', (tester) async {
    final controller = Get.put(FounderCommandCenterController());
    controller.chatMessages.add({
      'role': 'assistant',
      'content': jsonEncode(_blockedPlan(blockers: [
        {'code': 'connector_missing', 'target': 'tools_tab'},
      ])),
    });
    await pumpChat(tester, controller);

    final approveButton = find.byKey(const Key('automation_plan_approve_button'));
    expect(approveButton, findsOneWidget);
    expect(tester.widget<FilledButton>(approveButton).onPressed, isNull);

    expect(find.byKey(const Key('automation_plan_open_tools_tab')), findsOneWidget);
    expect(find.byKey(const Key('automation_plan_open_founder_profile')), findsNothing);
    expect(find.byKey(const Key('automation_plan_open_agents_tab')), findsNothing);

    expect(controller.requestedOperationsTabSeq.value, 0);
    await tester.tap(find.byKey(const Key('automation_plan_open_tools_tab')));
    await tester.pump();

    expect(controller.requestedOperationsTabSeq.value, 1);
    expect(controller.lastRequestedOperationsTab, HubOperationsTab.tools);

    // Bấm lại đúng blocker cũ vẫn phải phát tín hiệu (seq tăng tiếp, không bị Rx equality
    // chặn khi giá trị Tab không đổi).
    await tester.tap(find.byKey(const Key('automation_plan_open_tools_tab')));
    await tester.pump();
    expect(controller.requestedOperationsTabSeq.value, 2);
  });

  testWidgets('founder_profile blocker navigates to the real profile route', (tester) async {
    final controller = Get.put(FounderCommandCenterController());
    controller.chatMessages.add({
      'role': 'assistant',
      'content': jsonEncode(_blockedPlan(blockers: [
        {'code': 'founder_channel_unverified', 'target': 'founder_profile'},
      ])),
    });
    final observer = _RecordingNavigatorObserver();
    await pumpChat(tester, controller, observer: observer);

    await tester.tap(find.byKey(const Key('automation_plan_open_founder_profile')));
    await tester.pumpAndSettle();

    expect(observer.pushedRouteNames, contains(AppRoutes.profile));
  });

  testWidgets('agents_tab blocker signals the real controller (not a no-op)', (tester) async {
    final controller = Get.put(FounderCommandCenterController());
    controller.chatMessages.add({
      'role': 'assistant',
      'content': jsonEncode(_blockedPlan(blockers: [
        {'code': 'requires_new_agent', 'target': 'agents_tab'},
      ])),
    });
    await pumpChat(tester, controller);

    await tester.tap(find.byKey(const Key('automation_plan_open_agents_tab')));
    await tester.pump();

    expect(controller.requestedOperationsTabSeq.value, 1);
    expect(controller.lastRequestedOperationsTab, HubOperationsTab.agents);
  });

  testWidgets('multiple blockers at once render all matching secondary buttons',
      (tester) async {
    final controller = Get.put(FounderCommandCenterController());
    controller.chatMessages.add({
      'role': 'assistant',
      'content': jsonEncode(_blockedPlan(blockers: [
        {'code': 'founder_channel_unverified', 'target': 'founder_profile'},
        {'code': 'connector_missing', 'target': 'tools_tab'},
        {'code': 'requires_new_agent', 'target': 'agents_tab'},
      ])),
    });
    await pumpChat(tester, controller);

    expect(find.byKey(const Key('automation_plan_open_founder_profile')), findsOneWidget);
    expect(find.byKey(const Key('automation_plan_open_tools_tab')), findsOneWidget);
    expect(find.byKey(const Key('automation_plan_open_agents_tab')), findsOneWidget);
  });

  testWidgets('tolerates a message missing optional fields without crashing', (tester) async {
    final controller = Get.put(FounderCommandCenterController());
    controller.chatMessages.add({
      'role': 'assistant',
      'content': jsonEncode({
        'kind': 'automation_plan_proposal',
        'proposalId': 'prop_3',
        'projectId': 'p1',
        // 'plan' và 'readiness' bị thiếu hoàn toàn — output model lệch định dạng.
      }),
    });

    await pumpChat(tester, controller);
    await tester.pump();

    // Không crash: thẻ vẫn render (khoá) thay vì raw JSON hay lỗi.
    expect(tester.takeException(), isNull);
    expect(find.textContaining('"kind"'), findsNothing);
    final approveButton = find.byKey(const Key('automation_plan_approve_button'));
    expect(approveButton, findsOneWidget);
    expect(tester.widget<FilledButton>(approveButton).onPressed, isNull);
  });

  testWidgets('a plan_progress message is not mistaken for an automation plan proposal',
      (tester) async {
    final controller = Get.put(FounderCommandCenterController());
    controller.chatMessages.add({
      'role': 'assistant',
      'content': jsonEncode({
        'kind': 'plan_progress',
        'plan_id': 'plan_1',
        'done': ['Bước 1'],
        'pending_review': <String>[],
        'waiting_approval': <String>[],
        'blocked': <String>[],
      }),
    });

    await pumpChat(tester, controller);

    expect(find.byKey(const Key('automation_plan_approve_button')), findsNothing);
    expect(find.textContaining('Cập nhật tiến độ kế hoạch'), findsOneWidget);
  });

  testWidgets('a plain text message renders as before (regression)', (tester) async {
    final controller = Get.put(FounderCommandCenterController());
    controller.chatMessages.add({'role': 'assistant', 'content': 'Xin chào, tôi có thể giúp gì?'});

    await pumpChat(tester, controller);

    expect(find.text('Xin chào, tôi có thể giúp gì?'), findsOneWidget);
    expect(find.byKey(const Key('automation_plan_approve_button')), findsNothing);
  });
}

class _RecordingNavigatorObserver extends NavigatorObserver {
  final pushedRouteNames = <String>[];

  @override
  void didPush(Route<dynamic> route, Route<dynamic>? previousRoute) {
    final name = route.settings.name;
    if (name != null) pushedRouteNames.add(name);
    super.didPush(route, previousRoute);
  }
}
