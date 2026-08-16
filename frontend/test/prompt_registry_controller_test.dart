import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/core/network/api_client.dart';
import 'package:frontend/modules/prompts/controllers/prompt_registry_controller.dart';
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

  test('isOwner is true only when the cached role is owner', () async {
    final ownerController = PromptRegistryController(roleLoader: () async => 'owner');
    await ownerController.loadRole();
    expect(ownerController.isOwner.value, isTrue);

    final adminController = PromptRegistryController(roleLoader: () async => 'admin');
    await adminController.loadRole();
    expect(adminController.isOwner.value, isFalse);
  });

  test('loadPrompts populates the prompts list from the service', () async {
    ApiClient.client = MockClient((request) async {
      return http.Response(
        jsonEncode({
          'prompts': [
            {'domain': 'cosa', 'name': 'chat_language', 'is_overridden': false, 'is_wired': true},
          ],
        }),
        200,
      );
    });

    final controller = PromptRegistryController(roleLoader: () async => 'owner');
    await controller.loadPrompts();

    expect(controller.prompts.length, 1);
    expect(controller.prompts.first['domain'], 'cosa');
  });
}
