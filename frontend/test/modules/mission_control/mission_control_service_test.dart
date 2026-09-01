import 'dart:convert';
import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/core/network/api_client.dart';
import 'package:frontend/modules/mission_control/services/mission_control_service.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  late http.Client realClient;

  setUp(() {
    realClient = ApiClient.client;
    SharedPreferences.setMockInitialValues({});
  });

  tearDown(() {
    ApiClient.client = realClient;
  });

  group('MissionControlService', () {
    test('orchestrateMission successfully parses mission response', () async {
      const goal = 'Improve customer retention by 20%';

      ApiClient.client = MockClient((request) async {
        expect(request.method, 'POST');
        expect(request.url.path, '/agents/mission-control/orchestrate');

        final body = jsonDecode(request.body) as Map<String, dynamic>;
        expect(body['goal'], goal);

        return http.Response(
          jsonEncode({
            'mission_id': 'mis-001',
            'workspace_id': 'ws-123',
            'goal': goal,
            'diagnosis': 'Analysis shows customer pain points',
            'specialist_reports': {
              'sales': {'status': 'analyzed'},
              'support': {'status': 'analyzed'}
            },
            'priorities': ['urgent', 'high'],
            'action_plan': [
              {'step': 1, 'action': 'Implement retention program'},
              {'step': 2, 'action': 'Monitor metrics'}
            ],
            'required_approvals': [
              {'id': 'app-1', 'role': 'founder'}
            ],
            'status': 'planned',
          }),
          200,
        );
      });

      final service = MissionControlService();
      final mission = await service.orchestrateMission(goal);

      expect(mission, isNotNull);
      expect(mission!.missionId, 'mis-001');
      expect(mission.workspaceId, 'ws-123');
      expect(mission.goal, goal);
      expect(mission.diagnosis, 'Analysis shows customer pain points');
      expect(mission.status, 'planned');
      expect(mission.priorities.length, 2);
      expect(mission.actionPlan.length, 2);
      expect(mission.requiredApprovals.length, 1);
    });

    test('orchestrateMission returns null on 400 error', () async {
      ApiClient.client = MockClient((request) async {
        return http.Response(
          jsonEncode({'error': 'Invalid goal'}),
          400,
        );
      });

      final service = MissionControlService();
      final mission = await service.orchestrateMission('Invalid goal');

      expect(mission, isNull);
    });

    test('orchestrateMission returns null on 500 error', () async {
      ApiClient.client = MockClient((request) async {
        return http.Response(
          jsonEncode({'error': 'Server error'}),
          500,
        );
      });

      final service = MissionControlService();
      final mission = await service.orchestrateMission('Some goal');

      expect(mission, isNull);
    });

    test('orchestrateMission handles non-JSON response', () async {
      ApiClient.client = MockClient((request) async {
        return http.Response('Not JSON', 200);
      });

      final service = MissionControlService();

      expect(
        () async => await service.orchestrateMission('Test goal'),
        throwsException,
      );
    });

    test('orchestrateMission returns null when response is not a map', () async {
      ApiClient.client = MockClient((request) async {
        return http.Response(
          jsonEncode(['array', 'response']),
          200,
        );
      });

      final service = MissionControlService();
      final mission = await service.orchestrateMission('Test goal');

      expect(mission, isNull);
    });

    test('orchestrateMission handles 201 Created response', () async {
      ApiClient.client = MockClient((request) async {
        return http.Response(
          jsonEncode({
            'mission_id': 'mis-new',
            'workspace_id': 'ws-456',
            'goal': 'Launch feature',
            'diagnosis': 'Ready to deploy',
            'specialist_reports': {},
            'priorities': [],
            'action_plan': [],
            'required_approvals': [],
            'status': 'created',
          }),
          201,
        );
      });

      final service = MissionControlService();
      final mission = await service.orchestrateMission('Launch feature');

      expect(mission, isNotNull);
      expect(mission!.missionId, 'mis-new');
    });

    test('orchestrateMission returns null on 204 No Content instead of throwing', () async {
      ApiClient.client = MockClient((request) async {
        return http.Response('', 204);
      });

      final service = MissionControlService();
      final mission = await service.orchestrateMission('Test goal');

      expect(mission, isNull);
    });

    test('orchestrateMission handles 299 boundary status code', () async {
      ApiClient.client = MockClient((request) async {
        return http.Response(
          jsonEncode({
            'mission_id': 'mis-boundary',
            'workspace_id': 'ws-789',
            'goal': 'Boundary test',
            'diagnosis': 'Testing 299 status',
            'specialist_reports': {},
            'priorities': [],
            'action_plan': [],
            'required_approvals': [],
            'status': 'accepted',
          }),
          299,
        );
      });

      final service = MissionControlService();
      final mission = await service.orchestrateMission('Test goal');

      expect(mission, isNotNull);
      expect(mission!.missionId, 'mis-boundary');
    });

    test('orchestrateMission returns null on 300 redirect status', () async {
      ApiClient.client = MockClient((request) async {
        return http.Response(
          jsonEncode({
            'mission_id': 'mis-redirect',
            'workspace_id': 'ws-999',
            'goal': 'Test',
            'diagnosis': 'Test',
            'specialist_reports': {},
            'priorities': [],
            'action_plan': [],
            'required_approvals': [],
            'status': 'pending',
          }),
          300,
        );
      });

      final service = MissionControlService();
      final mission = await service.orchestrateMission('Test goal');

      expect(mission, isNull);
    });

    test('orchestrateMission correctly encodes goal in request body', () async {
      String? capturedBody;
      ApiClient.client = MockClient((request) async {
        capturedBody = request.body;
        return http.Response(
          jsonEncode({
            'mission_id': 'test',
            'workspace_id': 'ws',
            'goal': 'test',
            'diagnosis': 'test',
            'specialist_reports': {},
            'priorities': [],
            'action_plan': [],
            'required_approvals': [],
            'status': 'test',
          }),
          200,
        );
      });

      final service = MissionControlService();
      await service.orchestrateMission('Test goal with "quotes" and special chars');

      final body = jsonDecode(capturedBody!) as Map<String, dynamic>;
      expect(body['goal'], 'Test goal with "quotes" and special chars');
    });
  });
}
