import 'dart:convert';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:frontend/core/network/api_client.dart';
import 'package:frontend/modules/settings/services/workspace_orientation_service.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  late http.Client originalClient;

  setUp(() {
    SharedPreferences.setMockInitialValues({'auth_token': 'test_token'});
    originalClient = ApiClient.client;
  });

  tearDown(() {
    ApiClient.client = originalClient;
  });

  group('WorkspaceOrientationService', () {
    test('fetch parses all-null fields and hasContent is false', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.method, 'GET');
        expect(request.url.path, '/identity/workspaces/ws_1');
        return http.Response(
          jsonEncode({
            'id': 'ws_1',
            'name': 'Workspace 1',
            'vision': null,
            'mission': null,
            'coreValues': null,
          }),
          200,
        );
      });

      final service = WorkspaceOrientationService();
      final result = await service.fetch('ws_1');

      expect(result.workspaceId, 'ws_1');
      expect(result.vision, isNull);
      expect(result.mission, isNull);
      expect(result.coreValues, isNull);
      expect(result.hasContent, isFalse);
    });

    test('update uses existing path and sends explicit null values', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.method, 'PATCH');
        expect(request.url.path, '/identity/workspaces/ws_1/company-identity');
        expect(
          request.body,
          '{"vision":null,"mission":"Focus on customer discovery","coreValues":null}',
        );
        return http.Response(
          jsonEncode({
            'id': 'ws_1',
            'name': 'Workspace 1',
            'vision': null,
            'mission': 'Focus on customer discovery',
            'coreValues': null,
          }),
          200,
        );
      });

      final service = WorkspaceOrientationService();
      final result = await service.update(
        'ws_1',
        vision: null,
        mission: 'Focus on customer discovery',
        coreValues: null,
      );

      expect(result.workspaceId, 'ws_1');
      expect(result.vision, isNull);
      expect(result.mission, 'Focus on customer discovery');
      expect(result.coreValues, isNull);
      expect(result.hasContent, isTrue);
    });

    test('throws WorkspaceOrientationException on non-200 response', () async {
      ApiClient.client = MockClient((request) async {
        return http.Response('Internal error', 500);
      });

      final service = WorkspaceOrientationService();
      expect(
        () => service.fetch('ws_1'),
        throwsA(isA<WorkspaceOrientationException>()),
      );
      expect(
        () => service.update(
          'ws_1',
          vision: 'Vision',
          mission: 'Mission',
          coreValues: 'Values',
        ),
        throwsA(isA<WorkspaceOrientationException>()),
      );
    });
  });
}
