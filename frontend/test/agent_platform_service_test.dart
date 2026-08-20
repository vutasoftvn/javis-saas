import 'dart:convert';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:frontend/core/network/api_client.dart';
import 'package:frontend/modules/agents/services/agent_platform_service.dart';

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({'auth_token': 'test_jwt_token'});
  });

  group('AgentPlatformService Tests', () {
    test('getAgents returns list of agents', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.url.path, '/api/v1/workforce/agents');
        return http.Response(
          jsonEncode([
            {'id': '101', 'key': 'founder', 'name': 'Founder Agent'},
            {'id': '102', 'key': 'sales', 'name': 'Sales Agent'},
          ]),
          200,
          headers: {'content-type': 'application/json'},
        );
      });

      final service = AgentPlatformService();
      final agents = await service.getAgents();

      expect(agents.length, 2);
      expect(agents.first['key'], 'founder');
    });

    test('getTools returns list of tools', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.url.path, '/api/v1/workforce/tools');
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
        expect(request.url.path, '/api/v1/workforce/routing/test');
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
