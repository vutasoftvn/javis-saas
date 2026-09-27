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
import 'package:frontend/modules/projects/services/project_operating_loop_service.dart';
import 'package:frontend/modules/settings/services/permissions_service.dart';
import 'package:frontend/modules/settings/services/settings_mvp_service.dart';
import 'package:get/get.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';

// Hub đợt 1 (spec 2026-09-27-hub-operations-workspace-design): card 4 tab lọc theo Project,
// hành động đi qua endpoint sẵn có, không hiển thị ID/enum thô.

class _FakeBackend {
  final requests = <String>[];
  final bodies = <String, Object?>{};
  String scheduleState = 'enabled';
  bool grantRevoked = false;
  String operationsState = 'ACTIVE';

  http.Response _json(Object body) =>
      http.Response(jsonEncode(body), 200, headers: {'content-type': 'application/json'});

  Map<String, dynamic> _schedule(String id, String projectId, String state) => {
        'id': id,
        'schedule_kind': 'daily',
        'timezone': 'Asia/Ho_Chi_Minh',
        'prompt_template': 'Tóm tắt email chưa đọc $id',
        'agent_profile': 'operations',
        'state': state,
        'project_id': projectId,
        'hour': 8,
        'minute': 0,
      };

  Future<http.Response> handle(http.Request r) async {
    final key = '${r.method} ${r.url.path}';
    requests.add(key);
    if (r.body.isNotEmpty) bodies[key] = jsonDecode(r.body);
    switch (key) {
      case 'GET /agent/schedules':
        return _json({
          'items': [
            _schedule('s1', 'p1', scheduleState),
            _schedule('s_other', 'p2', 'enabled'),
          ],
        });
      case 'GET /agent/schedules/s1/executions':
        return _json({
          'items': [
            {'id': 'e1', 'state': 'failed', 'scheduled_for': '2026-09-27T01:00:00Z'},
          ],
        });
      case 'POST /agent/schedules/s1/state':
        scheduleState = (jsonDecode(r.body) as Map)['state'] as String;
        return _json(_schedule('s1', 'p1', scheduleState));
      case 'PATCH /operations/projects/p1/operating-loop/tasks/t_agent/status':
        return _json({'id': 't_agent', 'status': 'done'});
      case 'GET /operations/projects/p1/agent-capability-grants':
        return _json({
          'items': [
            {
              'grantId': 'g1',
              'profileKey': 'operations',
              'capabilityId': 'okr.key_result.create',
              'label': {'vi': 'Tạo Key Result', 'en': 'Create Key Results'},
              'scope': 'PROJECT',
              'status': grantRevoked ? 'REVOKED' : 'ACTIVE',
            },
          ],
        });
      case 'POST /identity/agent-capability-grants/g1/revoke':
        grantRevoked = true;
        return _json({'grantId': 'g1', 'status': 'REVOKED'});
      case 'GET /operations/projects/p1/startup-team':
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
              'displayState': operationsState,
              'runtimeReadiness': 'READY',
              'assignmentVersion': 2,
              'pinnedSpecVersion': '1.5.0',
              'currentSpecVersion': '1.6.0',
              'specUpdateAvailable': true,
            },
          ],
        });
      case 'POST /operations/projects/p1/startup-team/operations/pause':
        operationsState = 'PAUSED';
        return _json({
          'profileKey': 'operations',
          'label': 'Vận hành',
          'displayState': 'PAUSED',
          'runtimeReadiness': 'READY',
          'assignmentVersion': 3,
        });
    }
    if (r.url.path.endsWith('/connectors')) {
      return _json({
        'data': [
          {'id': 'c1', 'connectorKey': 'email-read', 'state': 'enabled'},
        ],
        'meta': {'dataState': 'populated', 'observedAt': '2026-09-27T00:00:00Z'},
      });
    }
    return http.Response('{"code":"not_found"}', 404);
  }
}

LoopTask _task(String id, String title, {String status = 'todo', String? source}) => LoopTask(
      id: id,
      workspaceId: '1001',
      projectId: 'p1',
      title: title,
      status: status,
      priority: 'medium',
      timezone: 'UTC',
      source: source,
      createdAt: '2026-09-27T00:00:00Z',
      updatedAt: '2026-09-27T00:00:00Z',
    );

void main() {
  late _FakeBackend backend;
  late HubOperationsController controller;
  late RxnString projectId;
  late Rxn<ProjectOperatingLoop> loop;
  late int tasksReloaded;

  setUp(() async {
    SharedPreferences.setMockInitialValues({'workspace_id': '1001'});
    await SecureStorageService.write('auth_token', 'test-token');
    backend = _FakeBackend();
    final client = MvpRequestClient(httpClient: MockClient(backend.handle));
    controller = HubOperationsController(
      operationsService: HubOperationsService(client: client),
      loopService: ProjectOperatingLoopService(client: client),
      teamService: ProjectStartupTeamService(client: client),
      settingsService: SettingsMvpService(client: client),
      permissionsService: PermissionsService(client: client),
    );
    projectId = RxnString('p1');
    tasksReloaded = 0;
    loop = Rxn<ProjectOperatingLoop>(
      ProjectOperatingLoop(
        project: ProjectSummary.fromJson({'id': 'p1', 'title': 'Dự án'}),
        tasks: [
          _task('t_human', 'Gọi khách hàng A'),
          _task('t_agent', 'Soạn kế hoạch tuần', status: 'draft', source: 'ai_agent_proposal'),
        ],
      ),
    );
  });

  tearDown(Get.reset);

  Future<void> pump(WidgetTester tester) async {
    await tester.pumpWidget(
      GetMaterialApp(
        home: Scaffold(
          body: SingleChildScrollView(
            child: HubOperationsPanel(
              projectId: projectId,
              operatingLoop: loop,
              controller: controller,
              onTasksChanged: () async => tasksReloaded++,
            ),
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();
  }

  testWidgets('tasks tab filters agent drafts and changes status via the loop endpoint',
      (tester) async {
    await pump(tester);

    expect(find.text('Gọi khách hàng A'), findsOneWidget);
    expect(find.text('Soạn kế hoạch tuần'), findsOneWidget);
    expect(find.text('Nháp do agent'), findsOneWidget);
    expect(find.textContaining('t_agent'), findsNothing);

    await tester.tap(find.byKey(const Key('hub_ops_task_filter_agent')));
    await tester.pumpAndSettle();
    expect(find.text('Gọi khách hàng A'), findsNothing);

    await tester.tap(find.byKey(const Key('hub_ops_task_menu_t_agent')));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const Key('hub_ops_task_status_done')).last);
    await tester.pumpAndSettle();

    expect(
      backend.bodies['PATCH /operations/projects/p1/operating-loop/tasks/t_agent/status'],
      {'status': 'done'},
    );
    expect(tasksReloaded, 1);
  });

  testWidgets('schedules tab shows only this project, pauses and archives', (tester) async {
    await pump(tester);
    await tester.tap(find.byKey(const Key('hub_ops_tab_schedules')));
    await tester.pumpAndSettle();

    expect(find.byKey(const Key('hub_ops_schedule_s1')), findsOneWidget);
    expect(find.byKey(const Key('hub_ops_schedule_s_other')), findsNothing);
    expect(find.text('Hằng ngày lúc 08:00 · Vận hành'), findsOneWidget);
    expect(find.textContaining('thất bại'), findsOneWidget);

    await tester.tap(find.byKey(const Key('hub_ops_schedule_toggle_s1')));
    await tester.pumpAndSettle();
    expect(backend.bodies['POST /agent/schedules/s1/state'], {'state': 'paused'});
    expect(find.text('Tạm dừng'), findsWidgets);

    await tester.tap(find.byKey(const Key('hub_ops_schedule_archive_s1')));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const Key('hub_ops_confirm')));
    await tester.pumpAndSettle();
    expect(backend.bodies['POST /agent/schedules/s1/state'], {'state': 'archived'});
    expect(find.byKey(const Key('hub_ops_schedule_s1')), findsNothing);
  });

  testWidgets('tools tab lists connectors and revokes a grant after confirmation', (tester) async {
    await pump(tester);
    await tester.tap(find.byKey(const Key('hub_ops_tab_tools')));
    await tester.pumpAndSettle();

    expect(find.text('Email (đọc)'), findsOneWidget);
    expect(find.text('Tạo Key Result'), findsOneWidget);
    expect(find.text('okr.key_result.create'), findsNothing);
    expect(find.text('Vận hành'), findsOneWidget);

    await tester.tap(find.byKey(const Key('hub_ops_revoke_g1')));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const Key('hub_ops_confirm')));
    await tester.pumpAndSettle();

    expect(backend.requests, contains('POST /identity/agent-capability-grants/g1/revoke'));
    expect(find.text('Tạo Key Result'), findsNothing);
    expect(find.text('Đã thu hồi gần đây: 1 quyền'), findsOneWidget);
  });

  testWidgets('agents tab warns about a newer spec and pauses with the expected version',
      (tester) async {
    await pump(tester);
    await tester.tap(find.byKey(const Key('hub_ops_tab_agents')));
    await tester.pumpAndSettle();

    expect(find.text('Co-Founder'), findsNothing);
    expect(find.byKey(const Key('hub_ops_agent_update_operations')), findsOneWidget);
    expect(find.text('Phiên bản 1.5.0'), findsOneWidget);

    await tester.tap(find.byKey(const Key('hub_ops_agent_toggle_operations')));
    await tester.pumpAndSettle();
    expect(
      (backend.bodies['POST /operations/projects/p1/startup-team/operations/pause'] as Map)['expectedVersion'],
      2,
    );
    expect(find.text('Kích hoạt'), findsOneWidget);
  });

  testWidgets('switching project clears data and reloads opened tabs', (tester) async {
    await pump(tester);
    await tester.tap(find.byKey(const Key('hub_ops_tab_schedules')));
    await tester.pumpAndSettle();
    expect(find.byKey(const Key('hub_ops_schedule_s1')), findsOneWidget);

    projectId.value = 'p2';
    await tester.pumpAndSettle();
    expect(find.byKey(const Key('hub_ops_schedule_s1')), findsNothing);
    expect(find.byKey(const Key('hub_ops_schedule_s_other')), findsOneWidget);
  });
}
