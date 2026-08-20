import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/core/network/api_client.dart';
import 'package:frontend/core/services/ai_service.dart';
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

  group('getModels', () {
    test('returns the models list on success', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.url.path, '/api/v1/ai/models');
        return http.Response(
          jsonEncode({
            'models': [
              {'provider': 'openai', 'model': 'gpt-4o-mini'},
            ],
          }),
          200,
        );
      });

      final models = await AiService().getModels();

      expect(models, hasLength(1));
    });

    test('returns an empty list when workspace_id is missing', () async {
      SharedPreferences.setMockInitialValues({});
      ApiClient.client = MockClient((request) async {
        fail('should not call the API without a workspace_id');
      });

      final models = await AiService().getModels();

      expect(models, isEmpty);
    });

    test('returns an empty list on a non-200 response', () async {
      ApiClient.client = MockClient((request) async => http.Response('server error', 500));

      final models = await AiService().getModels();

      expect(models, isEmpty);
    });
  });

  group('getUsage', () {
    test('returns the usage payload on success', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.url.path, '/api/v1/ai/usage');
        return http.Response(jsonEncode({'tokens_used': 100}), 200);
      });

      final usage = await AiService().getUsage();

      expect(usage?['tokens_used'], 100);
    });

    test('returns null on a non-200 response', () async {
      ApiClient.client = MockClient((request) async => http.Response('not found', 404));

      final usage = await AiService().getUsage();

      expect(usage, isNull);
    });
  });
}
