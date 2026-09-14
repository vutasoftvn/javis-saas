import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/core/network/api_client.dart';
import 'package:frontend/modules/strategy/services/okr_service.dart';
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

  group('getOkrCycles', () {
    test('calls GET /operations/okr-cycles (not removed)', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.method, 'GET');
        expect(request.url.path, '/operations/okr-cycles');
        return http.Response(
          jsonEncode({
            'cycles': [
              {'id': 'cycle-1', 'name': 'Q3'},
            ],
          }),
          200,
        );
      });

      final result = await OkrService().getOkrCycles();

      expect(result.isSuccess, isTrue);
      expect(result.items.single['id'], 'cycle-1');
    });
  });

  group('createOkrCycle', () {
    test('calls POST /operations/okr-cycles with name/startDate/status', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.method, 'POST');
        expect(request.url.path, '/operations/okr-cycles');
        final body = jsonDecode(request.body) as Map<String, dynamic>;
        expect(body['name'], 'Q3 2026');
        expect(body['status'], 'active');
        return http.Response(jsonEncode({'id': 'cycle-1'}), 201);
      });

      final result = await OkrService().createOkrCycle(name: 'Q3 2026', status: 'active');

      expect(result['id'], 'cycle-1');
    });
  });

  group('getObjectives', () {
    test('calls GET /operations/objectives with cycle_id query', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.method, 'GET');
        expect(request.url.path, '/operations/objectives');
        expect(request.url.queryParameters['cycle_id'], 'cycle-1');
        return http.Response(
          jsonEncode({
            'objectives': [
              {'id': 'obj-1', 'cycleId': 'cycle-1'},
            ],
          }),
          200,
        );
      });

      final result = await OkrService().getObjectives(cycleId: 'cycle-1');

      expect(result.isSuccess, isTrue);
      expect(result.items.single['id'], 'obj-1');
    });
  });

  group('createObjective', () {
    test('calls POST /operations/objectives with filtered body', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.method, 'POST');
        expect(request.url.path, '/operations/objectives');
        final body = jsonDecode(request.body) as Map<String, dynamic>;
        expect(body['title'], 'Grow revenue');
        expect(body.containsKey('why'), isFalse);
        return http.Response(jsonEncode({'id': 'obj-1'}), 201);
      });

      final result = await OkrService().createObjective(title: 'Grow revenue');

      expect(result['id'], 'obj-1');
    });
  });

  group('publishObjective', () {
    test('calls POST /operations/objectives/:id/publish', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.method, 'POST');
        expect(request.url.path, '/operations/objectives/obj-1/publish');
        return http.Response(jsonEncode({'status': 'published'}), 200);
      });

      final result = await OkrService().publishObjective('obj-1');

      expect(result['status'], 'published');
    });
  });

  group('updateObjective', () {
    test('calls PUT /operations/objectives/:id without workspace_id query', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.method, 'PUT');
        expect(request.url.path, '/operations/objectives/obj-1');
        expect(request.url.query, isEmpty);
        final body = jsonDecode(request.body) as Map<String, dynamic>;
        expect(body['title'], 'New title');
        return http.Response(jsonEncode({'id': 'obj-1', 'title': 'New title'}), 200);
      });

      final result = await OkrService().updateObjective('obj-1', title: 'New title');

      expect(result['title'], 'New title');
    });
  });

  group('deleteObjective', () {
    test('calls DELETE /operations/objectives/:id', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.method, 'DELETE');
        expect(request.url.path, '/operations/objectives/obj-1');
        return http.Response('', 204);
      });

      await OkrService().deleteObjective('obj-1');
    });
  });

  group('getKeyResults', () {
    test('calls GET /operations/key-results with objective_id filter', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.method, 'GET');
        expect(request.url.path, '/operations/key-results');
        expect(request.url.queryParameters['objective_id'], 'obj-1');
        return http.Response(
          jsonEncode({
            'key_results': [
              {'id': 'kr-1', 'objectiveId': 'obj-1'},
            ],
          }),
          200,
        );
      });

      final result = await OkrService().getKeyResults(objectiveId: 'obj-1');

      expect(result.isSuccess, isTrue);
      expect(result.items.single['id'], 'kr-1');
    });
  });

  group('createKeyResult', () {
    test('calls POST /operations/objectives/:id/key-results with filtered body', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.method, 'POST');
        expect(request.url.path, '/operations/objectives/obj-1/key-results');
        final body = jsonDecode(request.body) as Map<String, dynamic>;
        expect(body['title'], 'Ship feature');
        expect(body.containsKey('unit'), isFalse);
        return http.Response(jsonEncode({'id': 'kr-1'}), 201);
      });

      final result = await OkrService().createKeyResult(objectiveId: 'obj-1', title: 'Ship feature');

      expect(result['id'], 'kr-1');
    });
  });

  group('checkinKeyResult', () {
    test('calls POST /operations/key-results/:id/checkin with value', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.method, 'POST');
        expect(request.url.path, '/operations/key-results/kr-1/checkin');
        final body = jsonDecode(request.body) as Map<String, dynamic>;
        expect(body['value'], 42.0);
        return http.Response(jsonEncode({'id': 'kr-1', 'currentValue': 42.0}), 200);
      });

      final result = await OkrService().checkinKeyResult('kr-1', 42.0);

      expect(result['currentValue'], 42.0);
    });
  });

  group('updateKeyResult', () {
    test('calls PUT /operations/key-results/:id without workspace_id query', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.method, 'PUT');
        expect(request.url.path, '/operations/key-results/kr-1');
        expect(request.url.query, isEmpty);
        final body = jsonDecode(request.body) as Map<String, dynamic>;
        expect(body['currentValue'], 10.0);
        return http.Response(jsonEncode({'id': 'kr-1', 'currentValue': 10.0}), 200);
      });

      final result = await OkrService().updateKeyResult('kr-1', currentValue: 10.0);

      expect(result['currentValue'], 10.0);
    });
  });

  group('deleteKeyResult', () {
    test('calls DELETE /operations/key-results/:id', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.method, 'DELETE');
        expect(request.url.path, '/operations/key-results/kr-1');
        return http.Response('', 204);
      });

      await OkrService().deleteKeyResult('kr-1');
    });
  });
}
