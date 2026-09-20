import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/core/network/api_client.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() {
    SharedPreferences.setMockInitialValues({'workspace_id': 'ws_1'});
  });

  group('Founder trial commercial flow tests', () {
    test('creates contact via ApiClient', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.method, 'POST');
        expect(request.url.path, '/commercial/contacts');
        return http.Response(
          jsonEncode({
            'data': {'id': 'contact-1', 'name': 'John Doe'},
            'meta': {'dataState': 'populated', 'observedAt': '2026-09-15T00:00:00Z', 'sources': []},
          }),
          201,
          headers: {'content-type': 'application/json'},
        );
      });

      final response = await ApiClient.post('/commercial/contacts', body: {'name': 'John Doe'});
      expect(response.statusCode, 201);
    });

    test('creates lead via ApiClient', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.method, 'POST');
        expect(request.url.path, '/commercial/leads');
        return http.Response(
          jsonEncode({
            'data': {'id': 'lead-1', 'name': 'Acme Corp'},
            'meta': {'dataState': 'populated', 'observedAt': '2026-09-15T00:00:00Z', 'sources': []},
          }),
          201,
          headers: {'content-type': 'application/json'},
        );
      });

      final response = await ApiClient.post('/commercial/leads', body: {'name': 'Acme Corp'});
      expect(response.statusCode, 201);
    });

    test('creates interview and submits evidence', () async {
      ApiClient.client = MockClient((request) async {
        final path = request.url.path;
        if (path == '/operations/projects/proj-1/interviews') {
          return http.Response(
            jsonEncode({
              'data': {'id': 'int-1', 'notes': 'Customer feedback'},
              'meta': {'dataState': 'populated', 'observedAt': '2026-09-15T00:00:00Z', 'sources': []},
            }),
            201,
            headers: {'content-type': 'application/json'},
          );
        }
        if (path == '/operations/interviews/int-1/submit-evidence') {
          return http.Response(
            jsonEncode({
              'data': {'evidenceId': 'ev-1'},
              'meta': {'dataState': 'populated', 'observedAt': '2026-09-15T00:00:00Z', 'sources': []},
            }),
            200,
            headers: {'content-type': 'application/json'},
          );
        }
        return http.Response('not found', 404);
      });

      final intRes = await ApiClient.post(
        '/operations/projects/proj-1/interviews',
        body: {'notes': 'Customer feedback'},
      );
      expect(intRes.statusCode, 201);

      final evRes = await ApiClient.post(
        '/operations/interviews/int-1/submit-evidence',
        body: {'claim': 'Confirmed pain point'},
      );
      expect(evRes.statusCode, 200);
    });
  });
}
