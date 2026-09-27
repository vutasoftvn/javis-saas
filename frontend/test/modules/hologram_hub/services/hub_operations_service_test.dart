import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/core/network/api_result.dart';
import 'package:frontend/core/network/mvp_request_client.dart';
import 'package:frontend/core/services/secure_storage_service.dart';
import 'package:frontend/modules/hologram_hub/models/hub_operations_models.dart';
import 'package:frontend/modules/hologram_hub/services/hub_operations_service.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';

// Hub đợt 1 — service cho tab Lịch và tab Công cụ đi qua endpoint generated (mvp-surface).
void main() {
  setUp(() async {
    SharedPreferences.setMockInitialValues({'workspace_id': '1001'});
    await SecureStorageService.write('auth_token', 'test-token');
  });

  http.Response json(Object body) => http.Response(
        jsonEncode(body),
        200,
        headers: {'content-type': 'application/json'},
      );

  test('lists schedules and decodes cadence fields', () async {
    final service = HubOperationsService(
      client: MvpRequestClient(
        httpClient: MockClient((request) async {
          expect(request.method, 'GET');
          expect(request.url.path, '/agent/schedules');
          return json({
            'items': [
              {
                'id': 'sched_1',
                'schedule_kind': 'daily',
                'timezone': 'Asia/Ho_Chi_Minh',
                'prompt_template': 'Tóm tắt email',
                'agent_profile': 'operations',
                'state': 'paused',
                'project_id': 'p1',
                'hour': 8,
                'minute': 0,
                'weekdays': [],
              },
            ],
            'total': 1,
          });
        }),
      ),
    );

    final res = await service.listSchedules();
    final items = res.dataOrNull!;
    expect(items.single.isPaused, isTrue);
    expect(items.single.hour, 8);
    expect(items.single.projectId, 'p1');
  });

  test('sets schedule state with the state in the body', () async {
    final service = HubOperationsService(
      client: MvpRequestClient(
        httpClient: MockClient((request) async {
          expect(request.method, 'POST');
          expect(request.url.path, '/agent/schedules/sched_1/state');
          expect(jsonDecode(request.body), {'state': 'archived'});
          return json({
            'id': 'sched_1',
            'schedule_kind': 'daily',
            'timezone': 'Asia/Ho_Chi_Minh',
            'prompt_template': 'x',
            'agent_profile': 'operations',
            'state': 'archived',
          });
        }),
      ),
    );

    final res = await service.setScheduleState('sched_1', 'archived');
    expect(res.dataOrNull!.isArchived, isTrue);
  });

  test('lists executions with a limit and flags failures', () async {
    final service = HubOperationsService(
      client: MvpRequestClient(
        httpClient: MockClient((request) async {
          expect(request.url.path, '/agent/schedules/sched_1/executions');
          expect(request.url.queryParameters['limit'], '1');
          return json({
            'items': [
              {'id': 'e1', 'state': 'blocked_reauth', 'scheduled_for': '2026-09-27T01:00:00Z'},
            ],
          });
        }),
      ),
    );

    final res = await service.listScheduleExecutions('sched_1', limit: 1);
    expect(res.dataOrNull!.single.isFailure, isTrue);
  });

  test('run-now posts to the schedule route', () async {
    var called = false;
    final service = HubOperationsService(
      client: MvpRequestClient(
        httpClient: MockClient((request) async {
          called = true;
          expect(request.method, 'POST');
          expect(request.url.path, '/agent/schedules/sched_1/run-now');
          return json({'id': 'e2', 'state': 'queued'});
        }),
      ),
    );
    expect((await service.runScheduleNow('sched_1')).isSuccess, isTrue);
    expect(called, isTrue);
  });

  test('lists project agent grants with vi/en labels', () async {
    final service = HubOperationsService(
      client: MvpRequestClient(
        httpClient: MockClient((request) async {
          expect(request.url.path, '/operations/projects/p1/agent-capability-grants');
          expect(request.headers['X-Workspace-Id'], '1001');
          return json({
            'items': [
              {
                'grantId': 'g1',
                'profileKey': 'operations',
                'capabilityId': 'okr.key_result.create',
                'label': {'vi': 'Tạo Key Result', 'en': 'Create Key Results'},
                'scope': 'PROJECT',
                'status': 'ACTIVE',
                'grantedAt': '2026-09-27T01:00:00Z',
              },
            ],
          });
        }),
      ),
    );

    final res = await service.listAgentGrants('p1');
    expect(res, isA<ApiSuccess<List<HubAgentGrant>>>());
    final grant = res.dataOrNull!.single;
    expect(grant.isActive, isTrue);
    expect(grant.label(isEn: false), 'Tạo Key Result');
    expect(grant.label(isEn: true), 'Create Key Results');
  });

  test('surfaces a failure instead of throwing on 4xx', () async {
    final service = HubOperationsService(
      client: MvpRequestClient(
        httpClient: MockClient((_) async => http.Response('{"code":"failed_precondition"}', 400)),
      ),
    );
    expect((await service.setScheduleState('sched_1', 'enabled')).isFailure, isTrue);
  });
}
