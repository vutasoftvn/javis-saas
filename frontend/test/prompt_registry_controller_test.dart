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

  test('loadPrompts populates prompts list, tabs and auto selects first item', () async {
    ApiClient.client = MockClient((request) async {
      if (request.url.path.contains('/platform/prompts/cosa/chat_language')) {
        return http.Response(
          jsonEncode({
            'domain': 'cosa',
            'name': 'chat_language',
            'content': 'Hello \${user_name}',
            'default_content': 'Hello \${user_name}',
            'is_wired': true,
            'revisions': [],
          }),
          200,
        );
      }
      return http.Response(
        jsonEncode({
          'prompts': [
            {'domain': 'cosa', 'name': 'chat_language', 'is_overridden': false, 'is_wired': true},
            {'domain': 'marketing', 'name': 'campaign', 'is_overridden': true, 'is_wired': false},
          ],
        }),
        200,
      );
    });

    final controller = PromptRegistryController(roleLoader: () async => 'owner');
    await controller.loadPrompts();

    expect(controller.prompts.length, 2);
    expect(controller.availableDomains, ['all', 'cosa', 'marketing']);
    expect(controller.getDomainCount('all'), 2);
    expect(controller.getDomainCount('marketing'), 1);
    expect(controller.selectedPrompt.value?['name'], 'chat_language');
    expect(controller.contentController.text, 'Hello \${user_name}');
    expect(controller.detectedVariables, ['user_name']);
  });

  test('filter by tab and search query works', () async {
    ApiClient.client = MockClient((request) async {
      if (request.url.path.contains('/platform/prompts/marketing/campaign')) {
        return http.Response(
          jsonEncode({
            'domain': 'marketing',
            'name': 'campaign',
            'content': 'Marketing prompt \${goal}',
            'default_content': 'Marketing prompt \${goal}',
            'is_wired': false,
            'revisions': [],
          }),
          200,
        );
      }
      if (request.url.path.contains('/platform/prompts/sales/outreach')) {
        return http.Response(
          jsonEncode({
            'domain': 'sales',
            'name': 'outreach',
            'content': 'Sales outreach \${client}',
            'default_content': 'Sales outreach \${client}',
            'is_wired': false,
            'revisions': [],
          }),
          200,
        );
      }
      if (request.url.path.contains('/platform/prompts/cosa/chat_language')) {
        return http.Response(
          jsonEncode({
            'domain': 'cosa',
            'name': 'chat_language',
            'content': 'Chat prompt',
            'default_content': 'Chat prompt',
            'is_wired': true,
            'revisions': [],
          }),
          200,
        );
      }
      return http.Response(
        jsonEncode({
          'prompts': [
            {'domain': 'cosa', 'name': 'chat_language', 'is_overridden': false, 'is_wired': true},
            {'domain': 'marketing', 'name': 'campaign', 'is_overridden': true, 'is_wired': false},
            {'domain': 'sales', 'name': 'outreach', 'is_overridden': false, 'is_wired': false},
          ],
        }),
        200,
      );
    });

    final controller = PromptRegistryController(roleLoader: () async => 'owner');
    await controller.loadPrompts(keepSelection: false);

    expect(controller.filteredPrompts.length, 3);

    controller.selectDomain('marketing');
    expect(controller.filteredPrompts.length, 1);
    expect(controller.filteredPrompts.first['name'], 'campaign');

    controller.selectDomain('all');
    controller.updateSearch('outreach');
    expect(controller.filteredPrompts.length, 1);
    expect(controller.filteredPrompts.first['name'], 'outreach');
  });

  test('tracking unsaved changes and save works for founder', () async {
    bool patchCalled = false;
    ApiClient.client = MockClient((request) async {
      if (request.method == 'PATCH') {
        patchCalled = true;
        return http.Response(
          jsonEncode({'domain': 'cosa', 'name': 'chat_language', 'content': 'New Prompt Content'}),
          200,
        );
      }
      if (request.url.path.contains('/platform/prompts/cosa/chat_language')) {
        return http.Response(
          jsonEncode({
            'domain': 'cosa',
            'name': 'chat_language',
            'content': patchCalled ? 'New Prompt Content' : 'Old Prompt Content',
            'default_content': 'Old Prompt Content',
            'is_wired': true,
            'revisions': [],
          }),
          200,
        );
      }
      return http.Response(
        jsonEncode({
          'prompts': [
            {'domain': 'cosa', 'name': 'chat_language', 'is_overridden': patchCalled, 'is_wired': true},
          ],
        }),
        200,
      );
    });

    final controller = PromptRegistryController(roleLoader: () async => 'owner');
    await controller.loadPrompts();

    expect(controller.hasUnsavedChanges.value, isFalse);

    controller.contentController.text = 'New Prompt Content';
    expect(controller.hasUnsavedChanges.value, isTrue);

    await controller.saveCurrentPrompt();

    expect(patchCalled, isTrue);
    expect(controller.hasUnsavedChanges.value, isFalse);
  });
}
