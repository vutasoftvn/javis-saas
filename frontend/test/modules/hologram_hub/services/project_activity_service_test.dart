import 'package:flutter_test/flutter_test.dart';
import 'package:get/get.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:frontend/core/network/api_client.dart';
import 'package:frontend/modules/hologram_hub/services/project_activity_service.dart';
import 'package:frontend/modules/hologram_hub/models/project_activity_models.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  late http.Client originalClient;

  setUp(() {
    SharedPreferences.setMockInitialValues({});
    Get.testMode = true;
    originalClient = ApiClient.client;
  });

  tearDown(() {
    ApiClient.client = originalClient;
    Get.reset();
  });

  group('ProjectActivityService', () {
    test('fetch returns project activity events with project scope', () async {
      ApiClient.client = MockClient((request) async {
        if (request.url.path == '/agent/projects/proj_a/activity' &&
            request.method == 'GET') {
          return http.Response(
            '''
            {
              "items": [
                {
                  "event_id": "evt_1",
                  "workspace_id": "ws_1",
                  "project_id": "proj_a",
                  "project_sequence": 1,
                  "kind": "run.queued",
                  "status": "pending",
                  "actor_id": "agent_1",
                  "actor_kind": "ai",
                  "correlation_id": "corr_1",
                  "summary": "Run started",
                  "occurred_at": "2026-09-11T10:00:00Z",
                  "recorded_at": "2026-09-11T10:00:00Z"
                }
              ],
              "total": 1
            }
            ''',
            200,
          );
        }
        return http.Response('not found', 404);
      });

      final service = ProjectActivityService();
      final events = await service.fetch('proj_a');

      expect(events.length, 1);
      expect(events[0].projectId, 'proj_a');
      expect(events[0].kind, 'run.queued');
    });

    test('fetch filters by afterSequence', () async {
      ApiClient.client = MockClient((request) async {
        final queryParams = request.url.queryParameters;
        expect(queryParams['after_project_sequence'], '5');
        return http.Response('{"items": [], "total": 0}', 200);
      });

      final service = ProjectActivityService();
      await service.fetch('proj_a', afterSequence: 5);
    });

    test('stream returns activity events using Last-Event-ID', () async {
      ApiClient.client = MockClient.streaming((request, bodyStream) async {
        final lastEventId = request.headers['Last-Event-ID'];
        expect(lastEventId, '2');

        final sseData =
            'id: 3\nevent: activity\ndata: {"event_id":"evt_3","workspace_id":"ws_1","project_id":"proj_a","project_sequence":3,"kind":"run.completed","status":"success","actor_id":"agent_1","actor_kind":"ai","correlation_id":"corr_1","summary":"Run completed","occurred_at":"2026-09-11T10:05:00Z","recorded_at":"2026-09-11T10:05:00Z"}\n\n';
        final bytes = sseData.codeUnits;

        return http.StreamedResponse(
          Stream<List<int>>.fromIterable([bytes]),
          200,
        );
      });

      final service = ProjectActivityService();
      final events = <ProjectActivityEvent>[];

      await service.stream('proj_a', afterSequence: 2).forEach((event) {
        events.add(event);
      });

      expect(events.isNotEmpty, isTrue);
      expect(events[0].projectId, 'proj_a');
    });
  });
}
