import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/core/lifecycle/lifecycle_service.dart';
import 'package:frontend/core/network/mvp_request_client.dart';
import 'package:frontend/core/services/secure_storage_service.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() async {
    SharedPreferences.setMockInitialValues({'workspace_id': 'ws1'});
    await SecureStorageService.write('auth_token', 'token');
  });

  group('LifecycleService path helpers', () {
    test('workspace lifecycle path uses /identity/workspaces/:id/lifecycle', () {
      expect(
        LifecycleService.pathFor(LifecycleEntityType.workspace, 'ws1'),
        '/identity/workspaces/ws1/lifecycle',
      );
    });

    test('project lifecycle path uses /operations/projects/:id/lifecycle', () {
      expect(
        LifecycleService.pathFor(LifecycleEntityType.project, 'p1'),
        '/operations/projects/p1/lifecycle',
      );
    });
  });

  group('getHistory', () {
    test('loads workspace history via generated endpoint', () async {
      final mock = MockClient((request) async {
        expect(request.method, 'GET');
        expect(request.url.path, '/identity/workspaces/ws1/lifecycle/events');
        return http.Response(
          jsonEncode({
            'data': {
              'items': [
                {'fromStage': 'W0_DISCOVERY', 'toStage': 'W1_FOUNDATION'},
              ],
            },
            'meta': {'dataState': 'populated', 'observedAt': '2026-09-15T00:00:00Z', 'sources': []},
          }),
          200,
          headers: {'content-type': 'application/json'},
        );
      });

      final service = LifecycleService(
        client: MvpRequestClient(httpClient: mock),
      );
      final history = await service.getHistory(LifecycleEntityType.workspace, 'ws1');

      expect(history['items'], isNotEmpty);
      expect(history['items'][0]['toStage'], 'W1_FOUNDATION');
    });

    test('loads project history via generated endpoint', () async {
      final mock = MockClient((request) async {
        expect(request.method, 'GET');
        expect(request.url.path, '/operations/projects/p1/lifecycle/events');
        return http.Response(
          jsonEncode({
            'data': {
              'items': [
                {'fromStage': 'P0_DISCOVERY', 'toStage': 'P1_PILOT'},
              ],
            },
            'meta': {'dataState': 'populated', 'observedAt': '2026-09-15T00:00:00Z', 'sources': []},
          }),
          200,
          headers: {'content-type': 'application/json'},
        );
      });

      final service = LifecycleService(
        client: MvpRequestClient(httpClient: mock),
      );
      final history = await service.getHistory(LifecycleEntityType.project, 'p1');

      expect(history['items'], isNotEmpty);
      expect(history['items'][0]['toStage'], 'P1_PILOT');
    });

    test('throws StateError on non-200 failure', () async {
      final mock = MockClient((request) async {
        return http.Response('Internal Error', 500);
      });

      final service = LifecycleService(
        client: MvpRequestClient(httpClient: mock),
      );

      expect(
        () => service.getHistory(LifecycleEntityType.workspace, 'ws1'),
        throwsA(isA<StateError>()),
      );
    });
  });

  group('transition', () {
    test('transitions workspace lifecycle stage with expected body and headers', () async {
      final mock = MockClient((request) async {
        expect(request.method, 'PATCH');
        expect(request.url.path, '/identity/workspaces/ws1/lifecycle');
        final body = jsonDecode(request.body) as Map<String, dynamic>;
        expect(body['toStage'], 'W1_FOUNDATION');
        expect(body['expectedStageVersion'], 2);
        expect(body['rationale'], 'Stage progression approved');

        return http.Response(
          jsonEncode({
            'data': {'stage': 'W1_FOUNDATION', 'version': 3},
            'meta': {'dataState': 'populated', 'observedAt': '2026-09-15T00:00:00Z', 'sources': []},
          }),
          200,
          headers: {'content-type': 'application/json'},
        );
      });

      final service = LifecycleService(
        client: MvpRequestClient(httpClient: mock),
      );
      final res = await service.transition(
        LifecycleEntityType.workspace,
        'ws1',
        toStage: 'W1_FOUNDATION',
        expectedStageVersion: 2,
        rationale: 'Stage progression approved',
      );

      expect(res['stage'], 'W1_FOUNDATION');
      expect(res['version'], 3);
    });

    test('transitions project lifecycle stage with expected body', () async {
      final mock = MockClient((request) async {
        expect(request.method, 'PATCH');
        expect(request.url.path, '/operations/projects/p1/lifecycle');
        final body = jsonDecode(request.body) as Map<String, dynamic>;
        expect(body['toStage'], 'P1_PILOT');
        expect(body['expectedStageVersion'], 1);

        return http.Response(
          jsonEncode({
            'data': {'stage': 'P1_PILOT', 'version': 2},
            'meta': {'dataState': 'populated', 'observedAt': '2026-09-15T00:00:00Z', 'sources': []},
          }),
          200,
          headers: {'content-type': 'application/json'},
        );
      });

      final service = LifecycleService(
        client: MvpRequestClient(httpClient: mock),
      );
      final res = await service.transition(
        LifecycleEntityType.project,
        'p1',
        toStage: 'P1_PILOT',
        expectedStageVersion: 1,
      );

      expect(res['stage'], 'P1_PILOT');
      expect(res['version'], 2);
    });

    test('throws StateError on transition failure', () async {
      final mock = MockClient((request) async {
        return http.Response('Precondition Failed', 412);
      });

      final service = LifecycleService(
        client: MvpRequestClient(httpClient: mock),
      );

      expect(
        () => service.transition(
          LifecycleEntityType.workspace,
          'ws1',
          toStage: 'W2_GROWTH',
          expectedStageVersion: 1,
        ),
        throwsA(isA<StateError>()),
      );
    });
  });
}
