import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/core/network/api_client.dart';
import 'package:frontend/modules/skills/services/prompt_registry_service.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  late http.Client realClient;

  setUp(() {
    realClient = ApiClient.client;
    SharedPreferences.setMockInitialValues({'workspace_id': '123'});
  });

  tearDown(() => ApiClient.client = realClient);

  test('lists domain prompts for the current workspace', () async {
    ApiClient.client = MockClient((request) async {
      expect(request.url.path, '/platform/prompts/');
      expect(request.url.queryParameters['workspace_id'], '123');
      return http.Response(
        jsonEncode({
          'prompts': [
            {'domain': 'cosa', 'name': 'chat_language', 'is_overridden': false, 'is_wired': true},
          ],
        }),
        200,
      );
    });

    final prompts = await PromptRegistryService().listPrompts();
    expect(prompts, [
      {'domain': 'cosa', 'name': 'chat_language', 'is_overridden': false, 'is_wired': true},
    ]);
  });

  test('throws PromptRegistryApiException on a non-2xx response', () async {
    ApiClient.client = MockClient((request) async {
      return http.Response(jsonEncode({'detail': 'Action requires owner role'}), 403);
    });

    expect(
      () => PromptRegistryService().updatePrompt('cosa', 'chat_language', 'new content'),
      throwsA(isA<PromptRegistryApiException>()),
    );
  });
}
