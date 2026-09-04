import 'dart:convert';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:frontend/core/network/api_client.dart';
import 'package:frontend/core/network/mvp_request_client.dart';
import 'package:frontend/core/services/secure_storage_service.dart';
import 'package:frontend/modules/agents/services/agent_platform_service.dart';
import 'package:frontend/modules/workforce/services/workforce_mvp_service.dart';

void main() {
  setUp(() async {
    SharedPreferences.setMockInitialValues({'workspace_id': 'ws_1001'});
    await SecureStorageService.write('auth_token', 'test-token');
  });

  group('AgentPlatformService Tests', () {
    // Task 13 — `getAgents` từng gọi thẳng `/workforce/agents` qua
    // `ApiClient` thô (mock ở trên). Task 12 (commit 3172fc42) migrate
    // `getAgents`/`listAgents` sang gọi `WorkforceMvpService.listRoster()`
    // (canonical `/agent/workforce/roster`) — test cũ mock sai path/transport
    // nên lúc nào cũng fail sau migrate. Coverage tương đương (đúng path,
    // đúng shape response) đã có ở
    // `test/modules/agents/agent_platform_service_test.dart` — test dưới đây
    // cập nhật theo cùng cách inject `WorkforceMvpService` để khớp hành vi
    // thật, không revert lại hành vi mới để test cũ pass.
    test('getAgents returns list of agents', () async {
      final mockHttp = MockClient((request) async {
        expect(request.url.path, '/agent/workforce/roster');
        return http.Response(
          jsonEncode({
            'data': [
              {
                'id': 101, 'key': 'founder', 'name': 'Founder Agent',
                'role_title': 'x', 'department': 'Operations', 'agent_type': 'specialist',
                'default_model_profile': 'reasoning', 'risk_level': 0,
                'status': 'available', 'enabled': true,
              },
              {
                'id': 102, 'key': 'sales', 'name': 'Sales Agent',
                'role_title': 'x', 'department': 'Commercial', 'agent_type': 'specialist',
                'default_model_profile': 'reasoning', 'risk_level': 0,
                'status': 'available', 'enabled': true,
              },
            ],
            'meta': {
              'data_state': 'populated',
              'observed_at': '2026-09-04T12:00:00.000Z',
              'sources': [],
            },
          }),
          200,
          headers: {'content-type': 'application/json'},
        );
      });

      final service = AgentPlatformService(
        workforceMvpService: WorkforceMvpService(client: MvpRequestClient(httpClient: mockHttp)),
      );
      final agents = await service.getAgents();

      expect(agents.length, 2);
      expect(agents.first['key'], 'founder');
    });

    test('getTools returns list of tools', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.url.path, '/workforce/tools');
        return http.Response(
          jsonEncode([
            {'id': '201', 'key': 'crm.search', 'transport': 'local', 'risk_level': 0},
            {'id': '202', 'key': 'email.send', 'transport': 'local', 'risk_level': 3},
          ]),
          200,
          headers: {'content-type': 'application/json'},
        );
      });

      final service = AgentPlatformService();
      final tools = await service.getTools();

      expect(tools.length, 2);
      expect(tools.last['key'], 'email.send');
      expect(tools.last['risk_level'], 3);
    });

    test('testRouting returns classified intent', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.url.path, '/workforce/routing/test');
        final body = jsonDecode(request.body);
        expect(body['message'], 'Chào COSA');
        return http.Response(
          jsonEncode({
            'intent': 'GENERAL_CHAT',
            'confidence': 1.0,
            'target_agent_key': 'general',
          }),
          200,
          headers: {'content-type': 'application/json'},
        );
      });

      final service = AgentPlatformService();
      final decision = await service.testRouting('Chào COSA');

      expect(decision, isNotNull);
      expect(decision!['intent'], 'GENERAL_CHAT');
      expect(decision['target_agent_key'], 'general');
    });
  });
}
