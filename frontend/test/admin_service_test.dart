import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/core/network/api_client.dart';
import 'package:frontend/data/services/admin_service.dart';
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

  group('getDiagnostics', () {
    test('returns the diagnostics payload on success', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.url.path, '/api/v1/admin/workspace-1/diagnostics');
        return http.Response(jsonEncode({'status': 'healthy'}), 200);
      });

      final diag = await AdminService().getDiagnostics();

      expect(diag?['status'], 'healthy');
    });

    test('returns null when workspace_id is missing', () async {
      SharedPreferences.setMockInitialValues({});
      ApiClient.client = MockClient((request) async {
        fail('should not call the API without a workspace_id');
      });

      final diag = await AdminService().getDiagnostics();

      expect(diag, isNull);
    });

    test('returns null on a non-200 response', () async {
      ApiClient.client = MockClient((request) async => http.Response('server error', 500));

      final diag = await AdminService().getDiagnostics();

      expect(diag, isNull);
    });
  });
}
