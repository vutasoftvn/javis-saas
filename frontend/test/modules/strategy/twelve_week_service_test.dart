import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/core/network/api_client.dart';
import 'package:frontend/modules/strategy/services/twelve_week_service.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';

// Task 8 (2026-09-14, PHẠM VI MỞ RỘNG) — twelve_week_service.dart không mồ
// côi: HubCommandMixin.loadActiveCycleTimeline() gọi getTwelveWeekCycles() và
// getCycleTimeline() thật qua StrategyService facade. Test này khoá lại 2
// method đã nối route thật (5 method còn lại vẫn gọi /execution/* sai,
// ngoài phạm vi — không test ở đây).
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

  group('getTwelveWeekCycles', () {
    test('calls GET /operations/workspaces/:workspaceId/cycles (not /execution/*)', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.method, 'GET');
        expect(request.url.path, '/operations/workspaces/workspace-1/cycles');
        return http.Response(
          jsonEncode({
            'cycles': [
              {'id': 'cycle-1', 'projectId': 'project-1', 'status': 'ACTIVE'},
            ],
          }),
          200,
        );
      });

      final result = await TwelveWeekService().getTwelveWeekCycles();

      expect(result.isSuccess, isTrue);
      expect(result.items.single['id'], 'cycle-1');
    });
  });

  group('getCycleTimeline', () {
    test('calls GET /operations/execution-cycle-view with projectId + cycleId query', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.method, 'GET');
        expect(request.url.path, '/operations/execution-cycle-view');
        expect(request.url.queryParameters['projectId'], 'project-1');
        expect(request.url.queryParameters['cycleId'], 'cycle-1');
        return http.Response(jsonEncode({'cycleId': 'cycle-1'}), 200);
      });

      final result = await TwelveWeekService().getCycleTimeline('cycle-1', projectId: 'project-1');

      expect(result['cycleId'], 'cycle-1');
    });

    test('swallows errors and returns empty map (safe no-throw behavior preserved)', () async {
      ApiClient.client = MockClient((request) async {
        return http.Response('', 500);
      });

      final result = await TwelveWeekService().getCycleTimeline('cycle-1', projectId: 'project-1');

      expect(result, isEmpty);
    });
  });
}
