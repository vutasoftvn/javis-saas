// Task 7 — `AgentsService.getOrgChart/getRuns` từng gọi `/workforce/org-chart`
// và `/workforce/runs` (thiếu prefix `/agent`) qua `ApiClient.get` thô, rơi
// nhầm vào business/company runtime thay vì AgentOS thật — 404 vĩnh viễn.
// `agents_controller.dart` (`getOrgChart()`, `getRuns()`) là consumer sống
// của hai method này. Route thật đã mount: `/agent/workforce/org-chart`,
// `/agent/workforce/runs` (`apps/cosa/api/workforce_routes.py`).
//
// Fix-review (2026-09-02) — bản đầu tiên vẫn nuốt `ApiFailure` thành
// `null`/`[]` bên trong service dù đã đi qua `WorkforceMvpService` (vốn có
// `ApiFailure` thật). `getOrgChart`/`getRuns` giờ trả thẳng `ApiResult<T>` —
// test dưới đây khoá đúng hành vi honest-failure-propagation tại boundary
// này (`agents_controller.dart` xử lý nhánh `ApiFailure` tường minh).
import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:frontend/core/network/api_result.dart';
import 'package:frontend/core/network/mvp_request_client.dart';
import 'package:frontend/core/services/secure_storage_service.dart';
import 'package:frontend/modules/agents/services/agents_service.dart';
import 'package:frontend/modules/workforce/services/workforce_mvp_service.dart';

void main() {
  setUp(() async {
    TestWidgetsFlutterBinding.ensureInitialized();
    SharedPreferences.setMockInitialValues({'workspace_id': 'ws_1001'});
    await SecureStorageService.write('auth_token', 'test-token');
  });

  test('getOrgChart calls the canonical /agent/workforce/org-chart path', () async {
    final mockHttp = MockClient((request) async {
      expect(request.url.path, '/agent/workforce/org-chart');
      return http.Response(
        jsonEncode({
          'data': {'root': 'founder_copilot'},
          'meta': {
            'data_state': 'populated',
            'observed_at': '2026-08-31T12:00:00.000Z',
            'sources': [
              {'kind': 'agent_db', 'ref': 'agent.workforce_assignments'},
            ],
          },
        }),
        200,
      );
    });
    final service = AgentsService(
      workforceMvpService: WorkforceMvpService(client: MvpRequestClient(httpClient: mockHttp)),
    );

    final result = await service.getOrgChart();

    expect(result, isA<ApiSuccess<Map<String, dynamic>>>());
    expect((result as ApiSuccess<Map<String, dynamic>>).data['root'], 'founder_copilot');
  });

  test('getOrgChart propagates a 404 as ApiFailure, never a fabricated empty chart', () async {
    final mockHttp = MockClient((request) async {
      return http.Response(jsonEncode({'message': 'not found'}), 404);
    });
    final service = AgentsService(
      workforceMvpService: WorkforceMvpService(client: MvpRequestClient(httpClient: mockHttp)),
    );

    final result = await service.getOrgChart();

    expect(result, isA<ApiFailure<Map<String, dynamic>>>());
  });

  test('getRuns calls the canonical /agent/workforce/runs path and decodes the MVP envelope', () async {
    final mockHttp = MockClient((request) async {
      expect(request.url.path, '/agent/workforce/runs');
      return http.Response(
        jsonEncode({
          'data': [
            {
              'run_id': 'run_1',
              'workspace_id': 'ws_1001',
              'agent_spec_id': 'spec_1',
              'agent_spec_version': 'v1',
              'definition_hash': 'hash1',
              'status': 'completed',
              'created_at': '2026-08-31T12:00:00.000Z',
            },
          ],
          'meta': {
            'data_state': 'populated',
            'observed_at': '2026-08-31T12:00:00.000Z',
            'sources': [
              {'kind': 'agent_db', 'ref': 'agent.runs'},
            ],
          },
        }),
        200,
      );
    });
    final service = AgentsService(
      workforceMvpService: WorkforceMvpService(client: MvpRequestClient(httpClient: mockHttp)),
    );

    final result = await service.getRuns();

    expect(result, isA<ApiSuccess<List<Map<String, dynamic>>>>());
    final runs = (result as ApiSuccess<List<Map<String, dynamic>>>).data;
    expect(runs, hasLength(1));
    expect(runs.single['run_id'], 'run_1');
  });

  test('getRuns propagates a 500 as ApiFailure, never a fabricated empty history', () async {
    var requested = '';
    final mockHttp = MockClient((request) async {
      requested = request.url.path;
      return http.Response(jsonEncode({'detail': 'boom'}), 500);
    });
    final service = AgentsService(
      workforceMvpService: WorkforceMvpService(client: MvpRequestClient(httpClient: mockHttp)),
    );

    final result = await service.getRuns();

    expect(requested, '/agent/workforce/runs');
    expect(result, isA<ApiFailure<List<Map<String, dynamic>>>>());
    expect((result as ApiFailure<List<Map<String, dynamic>>>).failure.statusCode, 500);
  });
}
