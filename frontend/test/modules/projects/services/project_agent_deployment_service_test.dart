import 'dart:convert';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:frontend/core/network/mvp_request_client.dart';
import 'package:frontend/core/network/api_result.dart';
import 'package:frontend/modules/projects/services/project_agent_deployment_service.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:frontend/core/services/secure_storage_service.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  setUp(() async { SharedPreferences.setMockInitialValues({'workspace_id': 'ws'}); await SecureStorageService.write('auth_token', 'token'); });
  test('deploy sends only an exact workspaceAgentId', () async {
    final httpClient = MockClient((request) async {
      expect(request.url.path, '/operations/projects/proj-1/agent-deployments');
      final body = jsonDecode(request.body) as Map<String, dynamic>;
      expect(body, {'workspaceAgentId': 'agent-1'});
      return http.Response(jsonEncode({'data': {'id': 'dep-1', 'workspaceId': 'ws-1', 'projectId': 'proj-1', 'workspaceAgentId': 'agent-1', 'state': 'ACTIVE', 'capabilityOverrides': [], 'version': 1}, 'meta': {'dataState': 'populated', 'observedAt': '2026-09-15T00:00:00Z', 'sources': []}}), 200, headers: {'content-type': 'application/json'});
    });
    final result = await ProjectAgentDeploymentService(client: MvpRequestClient(httpClient: httpClient)).deploy('proj-1', workspaceAgentId: 'agent-1');
    expect(result.isSuccess, isTrue);
  });
  test('deploy rejects a malformed success payload without an ID or state', () async {
    final httpClient = MockClient((request) async => http.Response(jsonEncode({'data': {}, 'meta': {'dataState': 'populated', 'observedAt': '2026-09-15T00:00:00Z', 'sources': []}}), 200, headers: {'content-type': 'application/json'}));
    final result = await ProjectAgentDeploymentService(client: MvpRequestClient(httpClient: httpClient)).deploy('proj-1', workspaceAgentId: 'agent-1');
    expect(result.isSuccess, isFalse);
    expect(result.failureOrNull?.code, ApiFailureCode.malformedResponse);
  });
}
