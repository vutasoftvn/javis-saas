import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/core/network/api_client.dart';
import 'package:frontend/modules/settings/services/audit_service.dart';
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

  group('getAuditEvents', () {
    test('forwards action/actorType/limit/offset as query params', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.url.path, '/api/v1/admin/workspace-1/audit-events');
        expect(request.url.queryParameters['limit'], '10');
        expect(request.url.queryParameters['offset'], '5');
        expect(request.url.queryParameters['action'], 'workflow.step.approve');
        expect(request.url.queryParameters['actor_type'], 'user');
        return http.Response(jsonEncode({'total': 0, 'events': []}), 200);
      });

      await AuditService().getAuditEvents(
        action: 'workflow.step.approve',
        actorType: 'user',
        limit: 10,
        offset: 5,
      );
    });

    test('returns an empty result when workspace_id is missing', () async {
      SharedPreferences.setMockInitialValues({});
      ApiClient.client = MockClient((request) async {
        fail('should not call the API without a workspace_id');
      });

      final result = await AuditService().getAuditEvents();

      expect(result, {'total': 0, 'events': []});
    });

    test('returns an empty result on a non-200 response', () async {
      ApiClient.client = MockClient((request) async => http.Response('server error', 500));

      final result = await AuditService().getAuditEvents();

      expect(result, {'total': 0, 'events': []});
    });
  });
}
