import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/core/network/mvp_request_client.dart';
import 'package:frontend/core/services/secure_storage_service.dart';
import 'package:frontend/modules/hologram_hub/controllers/hub_operations_controller.dart';
import 'package:frontend/modules/hologram_hub/services/hub_operations_service.dart';
import 'package:frontend/modules/hologram_hub/services/project_startup_team_service.dart';
import 'package:frontend/modules/hologram_hub/widgets/hub_operations_card.dart';
import 'package:frontend/modules/projects/models/project_operating_loop.dart';
import 'package:frontend/modules/projects/services/project_agent_deployment_service.dart';
import 'package:frontend/modules/projects/services/project_operating_loop_service.dart';
import 'package:frontend/modules/settings/services/permissions_service.dart';
import 'package:frontend/modules/settings/services/settings_mvp_service.dart';
import 'package:frontend/modules/skills/services/founder_asset_service.dart';
import 'package:get/get.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';

// Task 9 (C2) — nút "Tạo agent mới" trong tab Agent. Test double cho lớp gọi API (HTTP client)
// dùng chung 1 backend giả lập để có thể kiểm tra đúng thứ tự lệnh gửi đi
// CLONE -> EVALUATE -> PUBLISH -> workspace-agents -> agent-deployments (task-8-report.md mục
// "API/luồng C2"). KHÔNG có EDIT_DRAFT trong luồng mặc định — xem bình luận ở
// `_CreateAgentDialogState` (`hub_operations_card.dart`) cho lý do kỹ thuật (EDIT_DRAFT phía cosa
// REPLACE toàn bộ content mà client không có đủ dữ liệu để làm đúng).

/// Backend giả lập điều khiển được trạng thái trả về cho từng operation
/// (CLONE/EVALUATE/PUBLISH) qua [statusFor] — mặc định tất cả SUCCESS.
class _FakeFounderBackend {
  final List<String> requests = [];
  int _cmdSeq = 0;
  final Map<String, String> _commandOperation = {};

  /// operation -> status trả về khi poll events ('SUCCESS' | 'FAILED' | 'REJECTED' | null nghĩa
  /// là luôn PENDING, dùng để test timeout).
  final Map<String, String?> statusFor = {
    'CLONE': 'SUCCESS',
    'EVALUATE': 'SUCCESS',
    'PUBLISH': 'SUCCESS',
  };
  String? safeReasonCode;

  static const draftAssetId = 'custom.operations.cmd-1';
  static const draftVersion = '0.1.0';
  static const draftHash = 'sha256:draft';

  http.Response _json(Object body) =>
      http.Response(jsonEncode(body), 200, headers: {'content-type': 'application/json'});

  Future<http.Response> handle(http.Request r) async {
    final key = '${r.method} ${r.url.path}';

    if (key == 'GET /operations/projects/p1/startup-team') {
      requests.add(key);
      return _json({
        'items': [
          {
            'profileKey': 'founder_assistant',
            'label': 'Co-Founder',
            'displayState': 'CHAT_READY',
            'runtimeReadiness': 'READY',
          },
          {
            'profileKey': 'operations',
            'label': 'Vận hành',
            'displayState': 'TEMPLATE',
            'runtimeReadiness': 'READY',
            'assignmentVersion': 1,
          },
        ],
      });
    }

    if (key == 'POST /operations/founder/assets/commands') {
      final body = jsonDecode(r.body) as Map<String, dynamic>;
      final op = body['operation'] as String;
      requests.add('$key:$op');
      _cmdSeq += 1;
      final commandId = 'cmd-$_cmdSeq-$op';
      _commandOperation[commandId] = op;
      return _json({
        'commandId': commandId,
        'assetKind': body['assetKind'],
        'operation': op,
        'status': 'PENDING',
        'idempotencyKey': body['idempotencyKey'],
      });
    }

    if (key == 'GET /operations/founder/assets/events') {
      final commandId = r.url.queryParameters['commandId'];
      requests.add('$key:$commandId');
      final op = _commandOperation[commandId];
      final status = statusFor[op];
      if (status == null) {
        return _json({
          'events': [
            {'id': commandId, 'metadata': <String, dynamic>{}},
          ],
        });
      }
      return _json({
        'events': [
          {
            'id': commandId,
            'metadata': {
              'status': status,
              if (status == 'SUCCESS')
                'updatedAssetRef': {
                  'assetId': draftAssetId,
                  'version': draftVersion,
                  'definitionHash': draftHash,
                },
              if (status != 'SUCCESS' && safeReasonCode != null) 'safeReasonCode': safeReasonCode,
            },
          },
        ],
      });
    }

    if (key == 'POST /operations/founder/assets/workspace-agents') {
      requests.add(key);
      return _json({
        'id': 'wa-1',
        'agentAssetId': draftAssetId,
        'agentAssetVersion': draftVersion,
        'agentDefinitionHash': draftHash,
        'originKind': 'WORKSPACE_CLONE',
        'state': 'ACTIVE',
      });
    }

    if (key == 'POST /operations/projects/p1/agent-deployments') {
      requests.add(key);
      return _json({
        'id': 'dep-1',
        'workspaceId': '1001',
        'projectId': 'p1',
        'workspaceAgentId': 'wa-1',
        'state': 'ACTIVE',
        'capabilityOverrides': <dynamic>[],
        'version': 1,
      });
    }

    return http.Response('{"code":"not_found"}', 404);
  }
}

void main() {
  late _FakeFounderBackend backend;
  late HubOperationsController controller;

  setUp(() async {
    SharedPreferences.setMockInitialValues({'workspace_id': '1001'});
    await SecureStorageService.write('auth_token', 'test-token');
    backend = _FakeFounderBackend();
    final client = MvpRequestClient(httpClient: MockClient(backend.handle));
    controller = HubOperationsController(
      operationsService: HubOperationsService(client: client),
      loopService: ProjectOperatingLoopService(client: client),
      teamService: ProjectStartupTeamService(client: client),
      settingsService: SettingsMvpService(client: client),
      permissionsService: PermissionsService(client: client),
      founderAssetService: FounderAssetService(client: client),
      agentDeploymentService: ProjectAgentDeploymentService(client: client),
    );
  });

  tearDown(Get.reset);

  Future<void> pump(WidgetTester tester) async {
    await tester.pumpWidget(
      GetMaterialApp(
        home: Scaffold(
          body: HubOperationsPanel(
            projectId: RxnString('p1'),
            operatingLoop: Rxn<ProjectOperatingLoop>(),
            controller: controller,
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const Key('hub_ops_tab_agents')));
    await tester.pumpAndSettle();
  }

  /// Bơm đúng `count` lượt Timer của `Future.delayed(pollInterval)` bên trong wizard mà không
  /// chờ thời gian thật — `tester.pump` giả lập cả Timer lẫn microtask trong test binding.
  Future<void> pumpPolls(WidgetTester tester, int count) async {
    for (var i = 0; i < count; i++) {
      await tester.pump(const Duration(milliseconds: 1500));
    }
  }

  testWidgets('creates an agent end-to-end via CLONE -> EVALUATE -> PUBLISH -> workspace-agent -> deploy',
      (tester) async {
    await pump(tester);

    expect(find.byKey(const Key('hub_ops_create_agent')), findsOneWidget);
    await tester.tap(find.byKey(const Key('hub_ops_create_agent')));
    await tester.pumpAndSettle();

    await tester.tap(find.byKey(const Key('hub_ops_create_agent_source')));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Vận hành').last);
    await tester.pumpAndSettle();

    await tester.enterText(find.byKey(const Key('hub_ops_create_agent_name')), 'Vận hành gọn');
    await tester.enterText(
      find.byKey(const Key('hub_ops_create_agent_description')),
      'Agent riêng cho dự án',
    );

    await tester.tap(find.byKey(const Key('hub_ops_create_agent_submit')));
    // 3 lệnh POST commands (CLONE/EVALUATE/PUBLISH), mỗi lệnh 1 lượt poll SUCCESS ngay lập tức —
    // vẫn bơm vài nhịp cho các Future nối tiếp nhau chạy hết.
    for (var i = 0; i < 6; i++) {
      await tester.pump(const Duration(milliseconds: 50));
    }
    await tester.pumpAndSettle();
    // Toast thành công (Get.rawSnackbar) giữ 1 Timer 3s — bơm hết trước khi test kết thúc theo
    // từng nhịp nhỏ (một bước nhảy lớn làm lệch phép tính elapsed của AnimationController trong
    // fake clock), nếu không `AutomatedTestWidgetsFlutterBinding` báo lỗi "Timer is still pending".
    for (var i = 0; i < 8; i++) {
      await tester.pump(const Duration(milliseconds: 500));
    }

    expect(
      backend.requests,
      containsAllInOrder([
        'POST /operations/founder/assets/commands:CLONE',
        'GET /operations/founder/assets/events:cmd-1-CLONE',
        'POST /operations/founder/assets/commands:EVALUATE',
        'GET /operations/founder/assets/events:cmd-2-EVALUATE',
        'POST /operations/founder/assets/commands:PUBLISH',
        'GET /operations/founder/assets/events:cmd-3-PUBLISH',
        'POST /operations/founder/assets/workspace-agents',
        'POST /operations/projects/p1/agent-deployments',
      ]),
    );
    // Không có EDIT_DRAFT trong luồng mặc định (xem bình luận trong hub_operations_card.dart).
    expect(backend.requests.where((r) => r.contains(':EDIT_DRAFT')), isEmpty);

    // Dialog đã đóng và danh sách agent được nạp lại (loadTeam gọi lại GET startup-team).
    expect(find.byKey(const Key('hub_ops_create_agent_submit')), findsNothing);
    expect(
      backend.requests.where((r) => r == 'GET /operations/projects/p1/startup-team').length,
      greaterThanOrEqualTo(2),
    );
  });

  testWidgets('EVALUATE REJECTED stops the wizard and shows the reason — no PUBLISH call',
      (tester) async {
    backend.statusFor['EVALUATE'] = 'REJECTED';
    backend.safeReasonCode = 'AGENT_CAPABILITY_ESCALATION';

    await pump(tester);
    await tester.tap(find.byKey(const Key('hub_ops_create_agent')));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const Key('hub_ops_create_agent_source')));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Vận hành').last);
    await tester.pumpAndSettle();
    await tester.enterText(find.byKey(const Key('hub_ops_create_agent_name')), 'Vận hành gọn');

    await tester.tap(find.byKey(const Key('hub_ops_create_agent_submit')));
    for (var i = 0; i < 6; i++) {
      await tester.pump(const Duration(milliseconds: 50));
    }
    await tester.pumpAndSettle();

    expect(
      backend.requests,
      containsAllInOrder([
        'POST /operations/founder/assets/commands:CLONE',
        'POST /operations/founder/assets/commands:EVALUATE',
      ]),
    );
    expect(backend.requests.where((r) => r.contains(':PUBLISH')), isEmpty);
    expect(backend.requests.where((r) => r.contains('workspace-agents')), isEmpty);
    expect(backend.requests.where((r) => r.contains('agent-deployments')), isEmpty);

    // Dialog vẫn mở, hiện lý do từ chối cho founder.
    expect(find.byKey(const Key('hub_ops_create_agent_error')), findsOneWidget);
    expect(find.byKey(const Key('hub_ops_create_agent_submit')), findsOneWidget);
  });

  testWidgets('a stuck poll times out with a clear error instead of hanging forever',
      (tester) async {
    backend.statusFor['CLONE'] = null; // luôn PENDING

    await pump(tester);
    await tester.tap(find.byKey(const Key('hub_ops_create_agent')));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const Key('hub_ops_create_agent_source')));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Vận hành').last);
    await tester.pumpAndSettle();
    await tester.enterText(find.byKey(const Key('hub_ops_create_agent_name')), 'Vận hành gọn');

    await tester.tap(find.byKey(const Key('hub_ops_create_agent_submit')));
    await tester.pump();
    // pollTimeout mặc định 30s / pollInterval 1500ms = 20 lượt.
    await pumpPolls(tester, 21);
    await tester.pumpAndSettle();

    expect(find.byKey(const Key('hub_ops_create_agent_error')), findsOneWidget);
    expect(backend.requests.where((r) => r.contains(':EVALUATE')), isEmpty);
    // Dialog vẫn còn (không im lặng treo, không tự đóng khi lỗi).
    expect(find.byKey(const Key('hub_ops_create_agent_submit')), findsOneWidget);
  });
}
