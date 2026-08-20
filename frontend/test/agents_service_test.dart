import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/core/network/api_client.dart';
import 'package:frontend/modules/agents/services/agents_service.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  late http.Client realClient;

  setUp(() {
    realClient = ApiClient.client;
    SharedPreferences.setMockInitialValues({'workspace_id': 'workspace-1'});
  });

  tearDown(() {
    ApiClient.client = realClient;
  });

  group('getAgents', () {
    test('returns the agents list on success', () async {
      ApiClient.client = MockClient((request) async {
        if (request.url.path.contains('/agent-platform/agents')) {
          return http.Response('not found', 404);
        }
        expect(request.url.path, '/api/v1/workforce/agents');
        return http.Response(
          jsonEncode({
            'agents': [
              {'id': 'agent-1', 'name': 'CEO'},
            ],
          }),
          200,
        );
      });

      final agents = await AgentsService().getAgents();

      expect(agents, hasLength(1));
    });

    test('returns an empty list when workspace_id is missing', () async {
      SharedPreferences.setMockInitialValues({});
      ApiClient.client = MockClient((request) async {
        return http.Response('not found', 404);
      });

      final agents = await AgentsService().getAgents();

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
        expect(request.url.path, '/api/v1/agents/agent-1');
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
