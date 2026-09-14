import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/core/network/api_client.dart';
import 'package:frontend/modules/projects/services/executive_board_stage_suggestion_service.dart';
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

  group('getSuggestion', () {
    test('calls Task 9 project-scoped stage-suggestion endpoint and decodes body', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.method, 'GET');
        expect(request.url.path, '/operations/projects/proj-1/executive-board/stage-suggestion');
        return http.Response(
          jsonEncode({
            'stage': 'P2_BUILD',
            'toActivate': ['cfo', 'coo'],
            'toSuggestDeactivate': ['ciso'],
          }),
          200,
          headers: {'content-type': 'application/json'},
        );
      });

      final result = await ExecutiveBoardStageSuggestionService().getSuggestion('proj-1');

      expect(result['stage'], 'P2_BUILD');
      expect(result['toActivate'], ['cfo', 'coo']);
      expect(result['toSuggestDeactivate'], ['ciso']);
    });

    test('throws StateError when backend reports non-200', () async {
      ApiClient.client = MockClient((request) async {
        return http.Response('boom', 500);
      });

      expect(
        () => ExecutiveBoardStageSuggestionService().getSuggestion('proj-1'),
        throwsA(isA<StateError>()),
      );
    });
  });

  group('activateRole', () {
    test('calls workspace-scoped activation endpoint (Task 9/10), not project-scoped', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.method, 'POST');
        expect(
          request.url.path,
          '/operations/workspaces/ws-1/executive-roles/cfo/activate',
        );
        return http.Response('{}', 200, headers: {'content-type': 'application/json'});
      });

      await ExecutiveBoardStageSuggestionService().activateRole('ws-1', 'cfo');
      // Không throw nghĩa là request đã đi đúng endpoint workspace-scoped ở trên.
    });

    test('throws StateError when activation fails', () async {
      ApiClient.client = MockClient((request) async {
        return http.Response('nope', 412);
      });

      expect(
        () => ExecutiveBoardStageSuggestionService().activateRole('ws-1', 'cfo'),
        throwsA(isA<StateError>()),
      );
    });
  });
}
