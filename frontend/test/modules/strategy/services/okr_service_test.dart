import 'dart:convert';
import 'dart:io';
import 'dart:ui' show Locale;

import 'package:flutter_test/flutter_test.dart';
import 'package:get/get.dart';
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
    Get.locale = const Locale('vi', 'VN');
  });

  tearDown(() {
    ApiClient.client = realClient;
  });

  group('OKR Cycles', () {
    test('getOkrCycles returns cycles list on success', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.url.path, '/operations/okr-cycles');
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

    test('getOkrCycles returns cycles from MVP data wrapper', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.url.path, '/operations/okr-cycles');
        return http.Response(
          jsonEncode({
            'success': true,
            'data': [
              {'id': 'cycle-1', 'name': 'Q1 2026', 'status': 'active'},
            ],
          }),
          200,
        );
      });

      final result = await OkrService().getOkrCycles();

      expect(result.items, hasLength(1));
      expect(result.items.first['name'], 'Q1 2026');
    });

    test('getOkrCycles returns failure on 500 error', () async {
      ApiClient.client = MockClient(
        (request) async => http.Response('server error', 500),
      );

      final result = await OkrService().getOkrCycles();

      expect(result.items, isEmpty);
      expect(result.isUnavailable, isFalse);
      expect(result.errorMessage, isNotEmpty);
    });

    test('getOkrCycles returns failure on malformed JSON', () async {
      ApiClient.client = MockClient(
        (request) async => http.Response(
          'not json',
          200,
          headers: {'content-type': 'application/json'},
        ),
      );

      final result = await OkrService().getOkrCycles();

      expect(result.items, isEmpty);
      expect(result.errorMessage, isNotEmpty);
    });

    test('getOkrCycles returns failure on network error', () async {
      ApiClient.client = MockClient(
        (_) async => throw const SocketException('offline'),
      );

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
        expect(request.url.path, '/operations/okr-cycles');
        final body = jsonDecode(request.body);
        expect(body['name'], 'Q1 2026');
        expect(body['workspaceId'], 'workspace-1');
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
        expect(request.url.path, '/operations/objectives');
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
        return http.Response(
          jsonEncode({
            'objectives': [
              {'id': 'obj-1', 'cycleId': 'cycle-1', 'title': 'In cycle 1'},
              {'id': 'obj-2', 'cycleId': 'cycle-2', 'title': 'In cycle 2'},
            ],
          }),
          200,
        );
      });

      final result = await OkrService().getObjectives(cycleId: 'cycle-1');
      expect(result.items, hasLength(1));
      expect(result.items.first['id'], 'obj-1');
    });

    test('getObjectives returns failure on 500', () async {
      ApiClient.client = MockClient(
        (request) async => http.Response('server error', 500),
      );

      final result = await OkrService().getObjectives();

      expect(result.items, isEmpty);
      expect(result.errorMessage, isNotEmpty);
    });

    test('createObjective posts title and lineage fields', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.method, 'POST');
        expect(request.url.path, '/operations/objectives');
        final body = jsonDecode(request.body);
        expect(body['title'], 'New Strategic Objective');
        expect(body['cycleId'], 'cycle-1');
        expect(body['strategicObjectiveId'], 'strat-obj-1');
        expect(body['towsOptionId'], 'tows-opt-1');
        return http.Response(
          jsonEncode({
            'id': 'obj-2',
            'title': 'New Strategic Objective',
            'strategicObjectiveId': 'strat-obj-1',
            'towsOptionId': 'tows-opt-1',
            'status': 'DRAFT',
          }),
          200,
        );
      });

      final obj = await OkrService().createObjective(
        title: 'New Strategic Objective',
        cycleId: 'cycle-1',
        strategicObjectiveId: 'strat-obj-1',
        towsOptionId: 'tows-opt-1',
      );

      expect(obj['id'], 'obj-2');
      expect(obj['strategicObjectiveId'], 'strat-obj-1');
      expect(obj['towsOptionId'], 'tows-opt-1');
    });

    test(
      'publishObjective calls POST /operations/objectives/:id/publish',
      () async {
        ApiClient.client = MockClient((request) async {
          expect(request.method, 'POST');
          expect(request.url.path, '/operations/objectives/obj-1/publish');
          return http.Response(
            jsonEncode({
              'id': 'obj-1',
              'status': 'PUBLISHED',
              'publishedByMemberId': 'member-1',
            }),
            200,
          );
        });

        final published = await OkrService().publishObjective('obj-1');
        expect(published['status'], 'PUBLISHED');
      },
    );

    test('createObjective omits empty optional fields from body', () async {
      ApiClient.client = MockClient((request) async {
        final body = jsonDecode(request.body);
        expect(body.containsKey('strategicObjectiveId'), isFalse);
        expect(body.containsKey('towsOptionId'), isFalse);
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
        expect(request.url.path, '/operations/objectives/obj-1');
        return http.Response(
          jsonEncode({'id': 'obj-1', 'title': 'Updated'}),
          200,
        );
      });

      final obj = await OkrService().updateObjective('obj-1', title: 'Updated');

      expect(obj['title'], 'Updated');
    });

    test('deleteObjective calls DELETE on the endpoint', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.method, 'DELETE');
        expect(request.url.path, '/operations/objectives/obj-1');
        return http.Response('', 204);
      });

      await OkrService().deleteObjective('obj-1');
    });
  });

  group('Key Results', () {
    test('getKeyResults returns key results list', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.url.path, '/operations/key-results');
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

    test(
      'createKeyResult posts with defaults for numeric fields to objective route',
      () async {
        ApiClient.client = MockClient((request) async {
          expect(request.method, 'POST');
          expect(request.url.path, '/operations/objectives/obj-1/key-results');
          final body = jsonDecode(request.body);
          expect(body['objectiveId'], 'obj-1');
          expect(body['baselineValue'], 0);
          expect(body['targetValue'], 100);
          expect(body['scoringType'], 'LINEAR_INCREASE');
          expect(body['unit'], '%');
          return http.Response(jsonEncode({'id': 'kr-1'}), 200);
        });

        await OkrService().createKeyResult(objectiveId: 'obj-1');
      },
    );

    test('createKeyResult allows custom values for numeric fields', () async {
      ApiClient.client = MockClient((request) async {
        final body = jsonDecode(request.body);
        expect(body['baselineValue'], 12.5);
        expect(body['currentValue'], 600.0);
        expect(body['targetValue'], 99.9);
        expect(body['unit'], 'users');
        return http.Response(jsonEncode({'id': 'kr-2'}), 200);
      });

      await OkrService().createKeyResult(
        objectiveId: 'obj-1',
        baselineValue: 12.5,
        currentValue: 600.0,
        targetValue: 99.9,
        unit: 'users',
      );
    });

    test('updateKeyResult puts new values', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.method, 'PUT');
        expect(request.url.path, '/operations/key-results/kr-1');
        final body = jsonDecode(request.body);
        expect(body['currentValue'], 750.0);
        return http.Response(
          jsonEncode({'id': 'kr-1', 'currentValue': 750.0}),
          200,
        );
      });

      final kr = await OkrService().updateKeyResult(
        'kr-1',
        currentValue: 750.0,
      );

      expect(kr['currentValue'], 750.0);
    });

    test('deleteKeyResult calls DELETE on the endpoint', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.method, 'DELETE');
        expect(request.url.path, '/operations/key-results/kr-1');
        return http.Response('', 204);
      });

      await OkrService().deleteKeyResult('kr-1');
    });
  });

  group('AI OKR Generation', () {
    test(
      'generateAiOkrs fails closed while no governed backend capability exists',
      () async {
        ApiClient.client = MockClient((request) async {
          fail('AI generation must not call an undeclared backend endpoint');
        });

        expect(
          () => OkrService().generateAiOkrs(),
          throwsA(isA<UnsupportedError>()),
        );
      },
    );
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

    test(
      'decode falls back to status code message on malformed error response',
      () async {
        ApiClient.client = MockClient((request) async {
          return http.Response('plain text error', 500);
        });

        expect(
          () => OkrService().createObjective(title: 'Test'),
          throwsA(
            isA<StrategyApiException>().having(
              (e) => e.message,
              'message',
              contains('500'),
            ),
          ),
        );
      },
    );

    test('decodeList returns failure on missing workspace_id', () async {
      SharedPreferences.setMockInitialValues({});

      final result = await OkrService().getOkrCycles();

      expect(result.items, isEmpty);
      expect(result.errorMessage, contains('workspace'));
    });
  });
}
