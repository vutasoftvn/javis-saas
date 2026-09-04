// Task 7 — `AgentPlatformService.listApprovals/approveRequest/rejectRequest/
// getOrgChart` từng gọi thẳng `/workforce/...` (thiếu prefix `/agent`) qua
// `ApiClient.get/post` thô: normalizeEndpoint không nhận diện tiền tố này nên
// request rơi vào nhánh "business/local company runtime" (Encore company,
// port 4000) thay vì AgentOS thật (port 8001) — 404 vĩnh viễn, và
// `hub_control_plane_mixin.dart` (Founder Dashboard) đang là consumer sống
// của các method này. Route thật đã mount là `/agent/workforce/approvals`
// (`apps/cosa/api/workforce_routes.py`, mount qua `workforce_router` ở
// `apps/cosa/api/app.py:200`) — KHÔNG PHẢI `/agent/approvals`
// (`approval_routes.py`, `deprecated=True`, chưa từng được `include_router`).
//
// Fix-review (2026-09-02) — bản đầu tiên của lát cắt này vẫn giữ chữ ký cũ
// (`Future<Map?>`/`Future<List<Map>>`) và nuốt `ApiFailure` thành `null`/`[]`
// bên trong service — đúng lỗi mà việc migrate sang `WorkforceMvpService`
// (vốn cho `ApiFailure` thật) lẽ ra phải sửa. `approveRequest`/`rejectRequest`
// là mutation Founder chạm tới thật qua `hub_control_plane_mixin.dart`, nên
// một lỗi bị nuốt ở đây khiến approve/reject thất bại trông giống hệt thành
// công. 4 method này giờ trả thẳng `ApiResult<T>` — test dưới đây khoá đúng
// hành vi đó tại chính boundary này (không chỉ ở tầng `WorkforceMvpService`
// một lớp bên dưới).
import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:frontend/core/network/api_result.dart';
import 'package:frontend/core/network/mvp_request_client.dart';
import 'package:frontend/core/services/secure_storage_service.dart';
import 'package:frontend/modules/agents/services/agent_platform_service.dart';
import 'package:frontend/modules/workforce/services/workforce_mvp_service.dart';

void main() {
  setUp(() async {
    SharedPreferences.setMockInitialValues({'workspace_id': 'ws_1001'});
    await SecureStorageService.write('auth_token', 'test-token');
  });

  group('AgentPlatformService — canonical workforce approvals', () {
    test('listApprovals calls the canonical /agent/workforce/approvals path', () async {
      final mockHttp = MockClient((request) async {
        expect(request.url.path, '/agent/workforce/approvals');
        expect(request.url.queryParameters['status'], 'PENDING');
        return http.Response(
          jsonEncode({
            'data': [
              {
                'approval_id': 'app_1',
                'run_id': 'run_1',
                'action': 'send_email',
                'subject': 'Founder',
                'status': 'PENDING',
                'risk_level': 'medium',
                'required_role': 'admin',
                'policy_id': 'default',
                'created_at': '2026-08-31T12:00:00.000Z',
              },
            ],
            'meta': {
              'data_state': 'populated',
              'observed_at': '2026-08-31T12:00:00.000Z',
              'sources': [
                {'kind': 'agent_db', 'ref': 'agent.approvals'},
              ],
            },
          }),
          200,
        );
      });
      final service = AgentPlatformService(
        workforceMvpService: WorkforceMvpService(client: MvpRequestClient(httpClient: mockHttp)),
      );

      final result = await service.listApprovals();

      expect(result, isA<ApiSuccess<List<Map<String, dynamic>>>>());
      final approvals = (result as ApiSuccess<List<Map<String, dynamic>>>).data;
      expect(approvals, hasLength(1));
      expect(approvals.single['approval_id'], 'app_1');
    });

    test('listApprovals propagates a 500 as ApiFailure, never a fabricated empty list', () async {
      var requested = '';
      final mockHttp = MockClient((request) async {
        requested = request.url.path;
        return http.Response(jsonEncode({'detail': 'boom'}), 500);
      });
      final service = AgentPlatformService(
        workforceMvpService: WorkforceMvpService(client: MvpRequestClient(httpClient: mockHttp)),
      );

      final result = await service.listApprovals();

      expect(requested, '/agent/workforce/approvals');
      expect(result, isA<ApiFailure<List<Map<String, dynamic>>>>());
      expect((result as ApiFailure<List<Map<String, dynamic>>>).failure.statusCode, 500);
    });

    test('approveRequest posts a decision to the canonical endpoint with approved=true', () async {
      final mockHttp = MockClient((request) async {
        expect(request.method, 'POST');
        expect(request.url.path, '/agent/workforce/approvals/1/decision');
        final body = jsonDecode(request.body) as Map<String, dynamic>;
        expect(body['approved'], isTrue);
        return http.Response(
          jsonEncode({
            'data': {
              'approval_id': 'app_1',
              'run_id': 'run_1',
              'status': 'approved',
              'decided_at': '2026-08-31T12:05:00.000Z',
            },
            'meta': {
              'data_state': 'populated',
              'observed_at': '2026-08-31T12:05:00.000Z',
              'sources': [
                {'kind': 'agent_db', 'ref': 'agent.approvals'},
              ],
            },
          }),
          200,
        );
      });
      final service = AgentPlatformService(
        workforceMvpService: WorkforceMvpService(client: MvpRequestClient(httpClient: mockHttp)),
      );

      final result = await service.approveRequest(1, comment: 'ok');

      expect(result, isA<ApiSuccess<Map<String, dynamic>>>());
      expect((result as ApiSuccess<Map<String, dynamic>>).data['status'], 'approved');
    });

    test('approveRequest propagates a failed decision as ApiFailure — a rejected/broken '
        'approve must never look like success to the Founder', () async {
      final mockHttp = MockClient((request) async {
        return http.Response(jsonEncode({'detail': 'Approval not found'}), 404);
      });
      final service = AgentPlatformService(
        workforceMvpService: WorkforceMvpService(client: MvpRequestClient(httpClient: mockHttp)),
      );

      final result = await service.approveRequest(1, comment: 'ok');

      expect(result, isA<ApiFailure<Map<String, dynamic>>>());
      expect((result as ApiFailure<Map<String, dynamic>>).failure.code, ApiFailureCode.notFound);
    });

    test('rejectRequest posts a decision to the canonical endpoint with approved=false', () async {
      final mockHttp = MockClient((request) async {
        expect(request.url.path, '/agent/workforce/approvals/2/decision');
        final body = jsonDecode(request.body) as Map<String, dynamic>;
        expect(body['approved'], isFalse);
        return http.Response(
          jsonEncode({
            'data': {
              'approval_id': 'app_2',
              'run_id': 'run_2',
              'status': 'rejected',
              'decided_at': '2026-08-31T12:05:00.000Z',
            },
            'meta': {
              'data_state': 'populated',
              'observed_at': '2026-08-31T12:05:00.000Z',
              'sources': [
                {'kind': 'agent_db', 'ref': 'agent.approvals'},
              ],
            },
          }),
          200,
        );
      });
      final service = AgentPlatformService(
        workforceMvpService: WorkforceMvpService(client: MvpRequestClient(httpClient: mockHttp)),
      );

      final result = await service.rejectRequest(2, comment: 'no');

      expect(result, isA<ApiSuccess<Map<String, dynamic>>>());
      expect((result as ApiSuccess<Map<String, dynamic>>).data['status'], 'rejected');
    });

    test('rejectRequest propagates a 500 as ApiFailure, never a silent no-op', () async {
      final mockHttp = MockClient((request) async {
        return http.Response('Server error', 500);
      });
      final service = AgentPlatformService(
        workforceMvpService: WorkforceMvpService(client: MvpRequestClient(httpClient: mockHttp)),
      );

      final result = await service.rejectRequest(2, comment: 'no');

      expect(result, isA<ApiFailure<Map<String, dynamic>>>());
    });
  });

  group('AgentPlatformService — canonical workforce org-chart', () {
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
      final service = AgentPlatformService(
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
      final service = AgentPlatformService(
        workforceMvpService: WorkforceMvpService(client: MvpRequestClient(httpClient: mockHttp)),
      );

      final result = await service.getOrgChart();

      expect(result, isA<ApiFailure<Map<String, dynamic>>>());
    });
  });

  group('AgentPlatformService — canonical workforce dashboard gaps (2026-09-04)', () {
    test('getDashboardSummary calls the canonical /agent/workforce/dashboard-summary path', () async {
      final mockHttp = MockClient((request) async {
        expect(request.url.path, '/agent/workforce/dashboard-summary');
        return http.Response(
          jsonEncode({
            'data': {
              'roster_total': 6, 'roster_active': 1, 'open_exceptions': 0,
              'pending_approvals': 0, 'work_products_total': 0,
            },
            'meta': {'data_state': 'populated', 'observed_at': '2026-09-04T12:00:00.000Z', 'sources': []},
          }),
          200,
        );
      });
      final service = AgentPlatformService(
        workforceMvpService: WorkforceMvpService(client: MvpRequestClient(httpClient: mockHttp)),
      );

      final result = await service.getDashboardSummary();

      expect(result, isNotNull);
      expect(result!['roster_total'], 6);
    });

    test('listAgents calls the canonical /agent/workforce/roster path, not /workforce/agents', () async {
      final mockHttp = MockClient((request) async {
        expect(request.url.path, '/agent/workforce/roster');
        return http.Response(
          jsonEncode({
            'data': [
              {
                'id': 1, 'key': 'cashflow_planner', 'name': 'Cashflow Planner',
                'role_title': 'x', 'department': 'Finance', 'agent_type': 'specialist',
                'default_model_profile': 'reasoning', 'risk_level': 2,
                'status': 'available', 'enabled': true,
              },
            ],
            'meta': {'data_state': 'populated', 'observed_at': '2026-09-04T12:00:00.000Z', 'sources': []},
          }),
          200,
        );
      });
      final service = AgentPlatformService(
        workforceMvpService: WorkforceMvpService(client: MvpRequestClient(httpClient: mockHttp)),
      );

      final result = await service.listAgents();

      expect(result.single['key'], 'cashflow_planner');
      expect(result.single['department'], 'Finance');
    });

    test('listEscalations calls the canonical /agent/workforce/exceptions path', () async {
      final mockHttp = MockClient((request) async {
        expect(request.url.path, '/agent/workforce/exceptions');
        return http.Response(
          jsonEncode({
            'data': {
              'total': 0, 'founder_gate_count': 0, 'lead_notify_count': 0,
              'has_critical': false, 'escalations': [],
            },
            'meta': {'data_state': 'empty', 'observed_at': '2026-09-04T12:00:00.000Z', 'sources': []},
          }),
          200,
        );
      });
      final service = AgentPlatformService(
        workforceMvpService: WorkforceMvpService(client: MvpRequestClient(httpClient: mockHttp)),
      );

      final result = await service.listEscalations();

      expect(result['total'], 0);
      expect(result['escalations'], isEmpty);
    });
  });
}
