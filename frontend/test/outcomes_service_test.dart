import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/core/network/api_client.dart';
import 'package:frontend/data/services/outcomes_service.dart';
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

  group('getOutcomes', () {
    test('appends the status filter when provided', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.url.query, 'workspace_id=workspace-1&status=active');
        return http.Response(jsonEncode({'outcomes': []}), 200);
      });

      await OutcomesService().getOutcomes(status: 'active');
    });

    test('returns an empty list when workspace_id is missing', () async {
      SharedPreferences.setMockInitialValues({});
      ApiClient.client = MockClient((request) async {
        fail('should not call the API without a workspace_id');
      });

      final outcomes = await OutcomesService().getOutcomes();

      expect(outcomes, isEmpty);
    });
  });

  group('createOutcome', () {
    test('posts the outcome payload and returns the created outcome on 201', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.url.path, '/api/v1/outcomes');
        return http.Response(jsonEncode({'id': 'outcome-1'}), 201);
      });

      final outcome = await OutcomesService().createOutcome({'title': 'Ship v2'});

      expect(outcome?['id'], 'outcome-1');
    });
  });

  group('triggerRun', () {
    test('posts to the runs endpoint and returns the created run on 201', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.url.path, '/api/v1/outcomes/outcome-1/runs');
        return http.Response(jsonEncode({'id': 'run-1'}), 201);
      });

      final run = await OutcomesService().triggerRun('outcome-1');

      expect(run?['id'], 'run-1');
    });
  });

  group('getRunDetails', () {
    test('returns the run payload on success', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.url.path, '/api/v1/runs/run-1');
        return http.Response(jsonEncode({'status': 'completed'}), 200);
      });

      final run = await OutcomesService().getRunDetails('run-1');

      expect(run?['status'], 'completed');
    });
  });

  group('getRunEvents', () {
    test('returns the events list on success', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.url.path, '/api/v1/runs/run-1/events');
        return http.Response(
          jsonEncode({
            'events': [
              {'kind': 'started'},
            ],
          }),
          200,
        );
      });

      final events = await OutcomesService().getRunEvents('run-1');

      expect(events, hasLength(1));
    });
  });

  group('getArtifacts', () {
    test('appends the type filter when provided', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.url.queryParameters['type'], 'report');
        return http.Response(jsonEncode({'artifacts': []}), 200);
      });

      await OutcomesService().getArtifacts(type: 'report');
    });

    test('returns an empty list on a non-200 response', () async {
      ApiClient.client = MockClient((request) async => http.Response('server error', 500));

      final artifacts = await OutcomesService().getArtifacts();

      expect(artifacts, isEmpty);
    });
  });
}
