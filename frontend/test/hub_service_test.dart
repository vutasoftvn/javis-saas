import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/core/network/api_client.dart';
import 'package:frontend/data/services/hub_service.dart';
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

  group('getHubSummary', () {
    test('returns the summary payload on success', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.url.path, '/api/v1/admin/workspace-1/hub-summary');
        return http.Response(jsonEncode({'kpi_strip': {}}), 200);
      });

      final summary = await HubService().getHubSummary();

      expect(summary, isNotNull);
    });

    test('returns null when workspace_id is empty', () async {
      SharedPreferences.setMockInitialValues({'workspace_id': ''});
      ApiClient.client = MockClient((request) async {
        fail('should not call the API with an empty workspace_id');
      });

      final summary = await HubService().getHubSummary();

      expect(summary, isNull);
    });

    test('returns null when the request throws', () async {
      ApiClient.client = MockClient((request) async => throw Exception('network down'));

      final summary = await HubService().getHubSummary();

      expect(summary, isNull);
    });
  });
}
