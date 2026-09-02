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
// Test này khoá đúng canonical path + không âm thầm biến response hỏng
// thành danh sách rỗng bình thường.
import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';

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

      final approvals = await service.listApprovals();

      expect(approvals, hasLength(1));
      expect(approvals.single['approval_id'], 'app_1');
    });

    test('listApprovals does not turn a failed/legacy response into a fabricated empty list check', () async {
      // Không thể phân biệt "thật sự rỗng" vs "request lỗi" từ chữ ký cũ
      // (`Future<List<Map<String,dynamic>>>`) nhưng ít nhất phải log lỗi và
      // KHÔNG throw — hành vi được giữ tương thích ngược cho
      // `hub_control_plane_mixin.dart`. Route dùng vẫn phải là canonical.
      var requested = '';
      final mockHttp = MockClient((request) async {
        requested = request.url.path;
        return http.Response(jsonEncode({'detail': 'boom'}), 500);
      });
      final service = AgentPlatformService(
        workforceMvpService: WorkforceMvpService(client: MvpRequestClient(httpClient: mockHttp)),
      );

      final approvals = await service.listApprovals();

      expect(requested, '/agent/workforce/approvals');
      expect(approvals, isEmpty);
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

      expect(result?['status'], 'approved');
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

      expect(result?['status'], 'rejected');
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

      final chart = await service.getOrgChart();

      expect(chart?['root'], 'founder_copilot');
    });
  });
}
