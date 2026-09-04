import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/core/network/api_client.dart';
import 'package:frontend/core/network/mvp_request_client.dart';
import 'package:frontend/core/services/secure_storage_service.dart';
import 'package:frontend/modules/agents/services/agents_service.dart';
import 'package:frontend/modules/workforce/services/workforce_mvp_service.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  late http.Client realClient;

  setUp(() async {
    realClient = ApiClient.client;
    SharedPreferences.setMockInitialValues({'workspace_id': 'workspace-1'});
    await SecureStorageService.write('auth_token', 'test-token');
  });

  tearDown(() {
    ApiClient.client = realClient;
  });

  // Follow-up (2026-09-04) — `getAgents` từng gọi `/workforce/agents` (thiếu
  // prefix `/agent`, luôn 404) — route đó chưa từng có backend thật. Đã
  // migrate sang canonical `/agent/workforce/roster` qua `WorkforceMvpService`
  // (xem test canonical đầy đủ hơn ở
  // test/modules/agents/agents_service_test.dart). 2 test dưới đây cập nhật
  // theo hành vi mới, không revert lại route chết.
  group('getAgents', () {
    test('returns the agents list on success', () async {
      final mockHttp = MockClient((request) async {
        expect(request.url.path, '/agent/workforce/roster');
        return http.Response(
          jsonEncode({
            'data': [
              {
                'id': 1, 'key': 'ceo', 'name': 'CEO', 'role_title': 'x',
                'department': 'Executive', 'agent_type': 'specialist',
                'default_model_profile': 'reasoning', 'risk_level': 2,
                'status': 'available', 'enabled': true,
              },
            ],
            'meta': {'data_state': 'populated', 'observed_at': '2026-09-04T12:00:00.000Z', 'sources': []},
          }),
          200,
        );
      });

      final agents = await AgentsService(
        workforceMvpService: WorkforceMvpService(client: MvpRequestClient(httpClient: mockHttp)),
      ).getAgents();

      expect(agents, hasLength(1));
    });

    test('returns an empty list when the request fails', () async {
      final mockHttp = MockClient((request) async {
        return http.Response('not found', 404);
      });

      final agents = await AgentsService(
        workforceMvpService: WorkforceMvpService(client: MvpRequestClient(httpClient: mockHttp)),
      ).getAgents();

      expect(agents, isEmpty);
    });
  });

  group('createAgent', () {
    test('posts the agent data and returns the created agent on 201', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.method, 'POST');
        expect(jsonDecode(request.body), {'name': 'New Agent'});
        return http.Response(jsonEncode({'id': 'agent-2'}), 201);
      });

      final agent = await AgentsService().createAgent({'name': 'New Agent'});

      expect(agent?['id'], 'agent-2');
    });

    test('returns null when the backend does not return 201', () async {
      ApiClient.client = MockClient((request) async => http.Response('bad request', 400));

      final agent = await AgentsService().createAgent({'name': 'x'});

      expect(agent, isNull);
    });
  });

  group('updateAgent', () {
    test('sends a PATCH and returns the updated agent', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.method, 'PATCH');
        expect(request.url.path, '/agents/agent-1');
        return http.Response(jsonEncode({'id': 'agent-1', 'name': 'Updated'}), 200);
      });

      final agent = await AgentsService().updateAgent('agent-1', {'name': 'Updated'});

      expect(agent?['name'], 'Updated');
    });
  });

  group('deleteAgent', () {
    test('returns true on 204', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.method, 'DELETE');
        return http.Response('', 204);
      });

      final ok = await AgentsService().deleteAgent('agent-1');

      expect(ok, isTrue);
    });

    test('returns false on a non-204 response', () async {
      ApiClient.client = MockClient((request) async => http.Response('forbidden', 403));

      final ok = await AgentsService().deleteAgent('agent-1');

      expect(ok, isFalse);
    });
  });
}
