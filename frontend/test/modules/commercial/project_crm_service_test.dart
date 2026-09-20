import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/core/network/mvp_endpoints.g.dart';
import 'package:frontend/core/network/mvp_request_client.dart';
import 'package:frontend/core/services/secure_storage_service.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() async {
    SharedPreferences.setMockInitialValues({'workspace_id': 'ws_1'});
    await SecureStorageService.write('auth_token', 'token');
  });

  group('Project CRM Service tests', () {
    test('gets CRM schema via generated endpoint', () async {
      final mock = MockClient((request) async {
        expect(request.method, 'GET');
        expect(request.url.path, '/commercial/projects/proj-1/crm/schema');
        return http.Response(
          jsonEncode({
            'data': {'fieldDefinitions': [], 'leadSources': []},
            'meta': {'dataState': 'populated', 'observedAt': '2026-09-15T00:00:00Z', 'sources': []},
          }),
          200,
          headers: {'content-type': 'application/json'},
        );
      });

      final client = MvpRequestClient(httpClient: mock);
      final res = await client.request<Map<String, dynamic>>(
        MvpEndpoint.commercialProjectCrmSchemaGet,
        pathParams: {'projectId': 'proj-1'},
        decode: (json) => json as Map<String, dynamic>,
      );

      expect(res.isSuccess, isTrue);
    });

    test('creates lead via generated endpoint', () async {
      final mock = MockClient((request) async {
        expect(request.method, 'POST');
        expect(request.url.path, '/commercial/projects/proj-1/crm/leads');
        return http.Response(
          jsonEncode({
            'data': {'id': 'lead-1', 'name': 'Acme Corp'},
            'meta': {'dataState': 'populated', 'observedAt': '2026-09-15T00:00:00Z', 'sources': []},
          }),
          201,
          headers: {'content-type': 'application/json'},
        );
      });

      final client = MvpRequestClient(httpClient: mock);
      final res = await client.request<Map<String, dynamic>>(
        MvpEndpoint.commercialProjectCrmLeadsCreate,
        pathParams: {'projectId': 'proj-1'},
        body: {'name': 'Acme Corp'},
        decode: (json) => json as Map<String, dynamic>,
      );

      expect(res.isSuccess, isTrue);
    });
  });
}
