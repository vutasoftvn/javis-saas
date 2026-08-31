import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/core/network/api_client.dart';
import 'package:frontend/modules/strategy/services/strategy_service.dart';
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

  group('OKR Cycles', () {
    test('getOkrCycles returns cycles list on success', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.url.path, '/okrs/cycles');
        expect(request.url.queryParameters['workspace_id'], 'workspace-1');
        return http.Response(
          jsonEncode({
            'cycles': [
              {'id': 'cycle-1', 'name': 'Q1 2026', 'status': 'active'},
            ],
          }),
          200,
        );
      });

      final result = await OkrService().getOkrCycles();

      expect(result.items, hasLength(1));
      expect(result.items.first['name'], 'Q1 2026');
      expect(result.isUnavailable, isFalse);
      expect(result.errorMessage, isNull);
    });

    test('getOkrCycles returns failure on 500 error', () async {
      ApiClient.client = MockClient((request) async => http.Response('server error', 500));

      final result = await OkrService().getOkrCycles();

      expect(result.items, isEmpty);
      expect(result.isUnavailable, isFalse);
      expect(result.errorMessage, isNotEmpty);
    });

    test('getOkrCycles returns failure on malformed JSON', () async {
      ApiClient.client = MockClient(
        (request) async => http.Response('not json', 200, headers: {'content-type': 'application/json'}),
      );

      final result = await OkrService().getOkrCycles();

      expect(result.items, isEmpty);
      expect(result.errorMessage, isNotEmpty);
    });

    test('getOkrCycles returns failure on network error', () async {
      ApiClient.client = MockClient((_) async => throw const SocketException('offline'));

      final result = await OkrService().getOkrCycles();

      expect(result.items, isEmpty);
      expect(result.isUnavailable, isFalse);
      expect(result.errorMessage, isNotEmpty);
    });

    test('getOkrCycles returns failure when workspace_id is missing', () async {
      SharedPreferences.setMockInitialValues({});
      ApiClient.client = MockClient((request) async {
        fail('should not call the API without a workspace_id');
      });

      final result = await OkrService().getOkrCycles();

      expect(result.items, isEmpty);
      expect(result.errorMessage, contains('workspace'));
    });

    test('createOkrCycle posts name and optional dates', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.method, 'POST');
        expect(request.url.path, '/okrs/cycles');
        expect(request.url.queryParameters['workspace_id'], 'workspace-1');
        final body = jsonDecode(request.body);
        expect(body['name'], 'Q1 2026');
        expect(body['start_date'], startsWith('2026-01-01'));
        return http.Response(
          jsonEncode({'id': 'cycle-1', 'name': 'Q1 2026', 'status': 'active'}),
          200,
        );
      });

      final cycle = await OkrService().createOkrCycle(
        name: 'Q1 2026',
        startDate: DateTime(2026, 1, 1),
      );

      expect(cycle['id'], 'cycle-1');
      expect(cycle['name'], 'Q1 2026');
    });

    test('createOkrCycle throws StrategyApiException on failure', () async {
      ApiClient.client = MockClient((request) async {
        return http.Response(
          jsonEncode({'detail': 'Chu kỳ OKR đã tồn tại'}),
          409,
          headers: {'content-type': 'application/json; charset=utf-8'},
        );
      });

      expect(
        () => OkrService().createOkrCycle(name: 'Dup'),
        throwsA(
          isA<StrategyApiException>()
              .having((e) => e.statusCode, 'statusCode', 409)
              .having((e) => e.message, 'message', 'Chu kỳ OKR đã tồn tại'),
        ),
      );
    });
  });

  group('Objectives', () {
    test('getObjectives returns objectives list', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.url.path, '/okrs/objectives');
        expect(request.url.queryParameters['workspace_id'], 'workspace-1');
        return http.Response(
          jsonEncode({
            'objectives': [
              {'id': 'obj-1', 'title': 'Achieve Product-Market Fit'},
            ],
          }),
          200,
        );
      });

      final result = await OkrService().getObjectives();

      expect(result.items, hasLength(1));
      expect(result.items.first['title'], 'Achieve Product-Market Fit');
      expect(result.isUnavailable, isFalse);
    });

    test('getObjectives filters by cycle_id when provided', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.url.queryParameters['cycle_id'], 'cycle-1');
        return http.Response(jsonEncode({'objectives': []}), 200);
      });

      await OkrService().getObjectives(cycleId: 'cycle-1');
    });

    test('getObjectives returns failure on 500', () async {
      ApiClient.client = MockClient((request) async => http.Response('server error', 500));

      final result = await OkrService().getObjectives();

      expect(result.items, isEmpty);
      expect(result.errorMessage, isNotEmpty);
    });

    test('createObjective posts title and optional fields', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.method, 'POST');
        expect(request.url.path, '/okrs/objectives');
        final body = jsonDecode(request.body);
        expect(body['title'], 'New Objective');
        expect(body['cycle_id'], 'cycle-1');
        return http.Response(jsonEncode({'id': 'obj-2', 'title': 'New Objective'}), 200);
      });

      final obj = await OkrService().createObjective(
        title: 'New Objective',
        cycleId: 'cycle-1',
      );

      expect(obj['id'], 'obj-2');
    });

    test('createObjective omits empty optional fields from body', () async {
      ApiClient.client = MockClient((request) async {
        final body = jsonDecode(request.body);
        expect(body.containsKey('cycle_id'), isFalse);
        expect(body.containsKey('status'), isFalse);
        return http.Response(jsonEncode({'id': 'obj-3'}), 200);
      });

      await OkrService().createObjective(
        title: 'Objective',
        cycleId: '',
        status: '',
      );
    });

    test('updateObjective puts title and status to the endpoint', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.method, 'PUT');
        expect(request.url.path, '/okrs/objectives/obj-1');
        return http.Response(jsonEncode({'id': 'obj-1', 'title': 'Updated'}), 200);
      });

      final obj = await OkrService().updateObjective('obj-1', title: 'Updated');

      expect(obj['title'], 'Updated');
    });

    test('deleteObjective calls DELETE on the endpoint', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.method, 'DELETE');
        expect(request.url.path, '/okrs/objectives/obj-1');
        return http.Response('', 204);
      });

      await OkrService().deleteObjective('obj-1');
    });
  });

  group('Key Results', () {
    test('getKeyResults returns key results list', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.url.path, '/okrs/key-results');
        expect(request.url.queryParameters['workspace_id'], 'workspace-1');
        return http.Response(
          jsonEncode({
            'key_results': [
              {'id': 'kr-1', 'title': 'Increase DAU', 'target_value': 1000.0},
            ],
          }),
          200,
        );
      });

      final result = await OkrService().getKeyResults();

      expect(result.items, hasLength(1));
      expect(result.items.first['title'], 'Increase DAU');
      expect(result.isUnavailable, isFalse);
    });

    test('getKeyResults filters by objective_id when provided', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.url.queryParameters['objective_id'], 'obj-1');
        return http.Response(jsonEncode({'key_results': []}), 200);
      });

      await OkrService().getKeyResults(objectiveId: 'obj-1');
    });

    test('createKeyResult posts with defaults for numeric fields', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.method, 'POST');
        final body = jsonDecode(request.body);
        expect(body['objective_id'], 'obj-1');
        expect(body['baseline_value'], 0.0);
        expect(body['current_value'], 0.0);
        expect(body['target_value'], 100.0);
        expect(body['unit'], '%');
        expect(body['cadence'], 'weekly');
        expect(body['status'], 'active');
        return http.Response(jsonEncode({'id': 'kr-1'}), 200);
      });

      await OkrService().createKeyResult(objectiveId: 'obj-1');
    });

    test('createKeyResult allows custom values for numeric fields', () async {
      ApiClient.client = MockClient((request) async {
        final body = jsonDecode(request.body);
        expect(body['baseline_value'], 500.0);
        expect(body['current_value'], 600.0);
        expect(body['target_value'], 1000.0);
        expect(body['unit'], 'users');
        return http.Response(jsonEncode({'id': 'kr-2'}), 200);
      });

      await OkrService().createKeyResult(
        objectiveId: 'obj-1',
        baselineValue: 500.0,
        currentValue: 600.0,
        targetValue: 1000.0,
        unit: 'users',
      );
    });

    test('updateKeyResult puts new values', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.method, 'PUT');
        expect(request.url.path, '/okrs/key-results/kr-1');
        final body = jsonDecode(request.body);
        expect(body['current_value'], 750.0);
        return http.Response(jsonEncode({'id': 'kr-1', 'current_value': 750.0}), 200);
      });

      final kr = await OkrService().updateKeyResult('kr-1', currentValue: 750.0);

      expect(kr['current_value'], 750.0);
    });

    test('deleteKeyResult calls DELETE on the endpoint', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.method, 'DELETE');
        expect(request.url.path, '/okrs/key-results/kr-1');
        return http.Response('', 204);
      });

      await OkrService().deleteKeyResult('kr-1');
    });
  });

  group('AI OKR Generation', () {
    test('generateAiOkrs posts with default counts', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.method, 'POST');
        expect(request.url.path, '/okrs/generate-ai');
        final body = jsonDecode(request.body);
        expect(body['objectives_count'], 2);
        expect(body['krs_per_objective_count'], 3);
        return http.Response(
          jsonEncode({
            'objectives': [
              {'id': 'obj-1', 'title': 'Generated Objective'},
            ],
          }),
          200,
        );
      });

      final result = await OkrService().generateAiOkrs();

      expect(result['objectives'], isNotEmpty);
    });

    test('generateAiOkrs includes towsId when provided', () async {
      ApiClient.client = MockClient((request) async {
        final body = jsonDecode(request.body);
        expect(body['tows_id'], 'tows-1');
        return http.Response(jsonEncode({'objectives': []}), 200);
      });

      await OkrService().generateAiOkrs(towsId: 'tows-1');
    });

    test('generateAiOkrs omits empty towsId', () async {
      ApiClient.client = MockClient((request) async {
        final body = jsonDecode(request.body);
        expect(body.containsKey('tows_id'), isFalse);
        return http.Response(jsonEncode({'objectives': []}), 200);
      });

      await OkrService().generateAiOkrs(towsId: '');
    });

    test('generateAiOkrs includes cycleId when provided', () async {
      ApiClient.client = MockClient((request) async {
        final body = jsonDecode(request.body);
        expect(body['cycle_id'], 'cycle-1');
        return http.Response(jsonEncode({'objectives': []}), 200);
      });

      await OkrService().generateAiOkrs(cycleId: 'cycle-1');
    });

    test('generateAiOkrs throws exception when workspace_id is missing', () async {
      SharedPreferences.setMockInitialValues({});
      ApiClient.client = MockClient((request) async {
        fail('should not call API without workspace_id');
      });

      expect(
        () => OkrService().generateAiOkrs(),
        throwsA(isA<StrategyApiException>()),
      );
    });
  });

  group('Error Handling', () {
    test('decode throws StrategyApiException on 400 with detail', () async {
      ApiClient.client = MockClient((request) async {
        return http.Response(
          jsonEncode({'detail': 'Invalid request'}),
          400,
          headers: {'content-type': 'application/json; charset=utf-8'},
        );
      });

      expect(
        () => OkrService().createObjective(title: 'Test'),
        throwsA(
          isA<StrategyApiException>()
              .having((e) => e.statusCode, 'statusCode', 400)
              .having((e) => e.message, 'message', 'Invalid request'),
        ),
      );
    });

    test('decode falls back to status code message on malformed error response', () async {
      ApiClient.client = MockClient((request) async {
        return http.Response('plain text error', 500);
      });

      expect(
        () => OkrService().createObjective(title: 'Test'),
        throwsA(
          isA<StrategyApiException>()
              .having((e) => e.message, 'message', contains('500')),
        ),
      );
    });

    test('decodeList returns failure on missing workspace_id', () async {
      SharedPreferences.setMockInitialValues({});

      final result = await OkrService().getOkrCycles();

      expect(result.items, isEmpty);
      expect(result.errorMessage, contains('workspace'));
    });
  });
}
