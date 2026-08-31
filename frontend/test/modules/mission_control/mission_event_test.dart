import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/modules/mission_control/models/mission_event.dart';

void main() {
  group('MissionEvent', () {
    test('fromJson parses minimal required fields', () {
      final json = {
        'event_id': 'evt-001',
        'run_id': 'run-123',
        'event_type': 'mission_started',
        'timestamp': '2026-09-01T10:00:00Z',
      };

      final event = MissionEvent.fromJson(json);

      expect(event.eventId, 'evt-001');
      expect(event.runId, 'run-123');
      expect(event.agentKey, 'chief_of_staff'); // default value
      expect(event.eventType, 'mission_started');
      expect(event.timestamp, '2026-09-01T10:00:00Z');
      expect(event.data, isEmpty);
    });

    test('fromJson parses with all fields including data', () {
      final json = {
        'event_id': 'evt-002',
        'run_id': 'run-456',
        'agent_key': 'specialist_agent',
        'event_type': 'mission_completed',
        'timestamp': '2026-09-01T11:00:00Z',
        'data': {
          'status': 'completed',
          'duration_ms': 5000,
          'metrics': {'success_rate': 0.95}
        },
      };

      final event = MissionEvent.fromJson(json);

      expect(event.eventId, 'evt-002');
      expect(event.runId, 'run-456');
      expect(event.agentKey, 'specialist_agent');
      expect(event.eventType, 'mission_completed');
      expect(event.timestamp, '2026-09-01T11:00:00Z');
      expect(event.data['status'], 'completed');
      expect(event.data['duration_ms'], 5000);
      expect(event.data['metrics']['success_rate'], 0.95);
    });

    test('fromJson handles null/missing data field gracefully', () {
      final json = {
        'event_id': 'evt-003',
        'run_id': 'run-789',
        'event_type': 'error_occurred',
        'timestamp': '2026-09-01T12:00:00Z',
        'data': null,
      };

      final event = MissionEvent.fromJson(json);

      expect(event.data, isEmpty);
    });

    test('fromJson handles non-map data field as empty map', () {
      final json = {
        'event_id': 'evt-004',
        'run_id': 'run-999',
        'event_type': 'test_event',
        'timestamp': '2026-09-01T13:00:00Z',
        'data': 'not_a_map',
      };

      final event = MissionEvent.fromJson(json);

      expect(event.data, isEmpty);
    });

    test('fromJson converts values to strings safely', () {
      final json = {
        'event_id': 12345, // number instead of string
        'run_id': 67890,
        'agent_key': null,
        'event_type': 'test',
        'timestamp': '2026-09-01T14:00:00Z',
      };

      final event = MissionEvent.fromJson(json);

      expect(event.eventId, '12345');
      expect(event.runId, '67890');
      expect(event.agentKey, 'chief_of_staff'); // default when null
    });
  });

  group('ChiefOfStaffMission', () {
    test('fromJson parses minimal required fields', () {
      final json = {
        'mission_id': 'mission-001',
        'workspace_id': 'ws-123',
        'goal': 'Improve customer retention',
        'diagnosis': 'Customer churn increasing',
      };

      final mission = ChiefOfStaffMission.fromJson(json);

      expect(mission.missionId, 'mission-001');
      expect(mission.workspaceId, 'ws-123');
      expect(mission.goal, 'Improve customer retention');
      expect(mission.diagnosis, 'Customer churn increasing');
      expect(mission.specialistReports, isEmpty);
      expect(mission.priorities, isEmpty);
      expect(mission.actionPlan, isEmpty);
      expect(mission.requiredApprovals, isEmpty);
      expect(mission.status, 'completed'); // default value
    });

    test('fromJson parses with all fields', () {
      final json = {
        'mission_id': 'mission-002',
        'workspace_id': 'ws-456',
        'goal': 'Launch new product',
        'diagnosis': 'Market ready, team available',
        'specialist_reports': {
          'product': {'status': 'ready', 'version': '1.0'},
          'marketing': {'status': 'ready', 'budget': 100000}
        },
        'priorities': ['immediate', 'high'],
        'action_plan': [
          {'step': 1, 'description': 'Prepare release'},
          {'step': 2, 'description': 'Deploy'}
        ],
        'required_approvals': [
          {'id': 'app-001', 'role': 'founder'},
          {'id': 'app-002', 'role': 'cfo'}
        ],
        'status': 'in_progress',
      };

      final mission = ChiefOfStaffMission.fromJson(json);

      expect(mission.missionId, 'mission-002');
      expect(mission.workspaceId, 'ws-456');
      expect(mission.goal, 'Launch new product');
      expect(mission.diagnosis, 'Market ready, team available');
      expect(mission.specialistReports.length, 2);
      expect(mission.specialistReports['product']['status'], 'ready');
      expect(mission.priorities.length, 2);
      expect(mission.priorities.first, 'immediate');
      expect(mission.actionPlan.length, 2);
      expect(mission.requiredApprovals.length, 2);
      expect(mission.status, 'in_progress');
    });

    test('fromJson handles missing array fields', () {
      final json = {
        'mission_id': 'mission-003',
        'workspace_id': 'ws-789',
        'goal': 'Test mission',
        'diagnosis': 'Test diagnosis',
        'priorities': null,
        'action_plan': 'not_an_array',
      };

      final mission = ChiefOfStaffMission.fromJson(json);

      expect(mission.priorities, isEmpty);
      expect(mission.actionPlan, isEmpty);
    });

    test('fromJson handles missing specialist_reports field', () {
      final json = {
        'mission_id': 'mission-004',
        'workspace_id': 'ws-999',
        'goal': 'Another test',
        'diagnosis': 'Diagnosis here',
      };

      final mission = ChiefOfStaffMission.fromJson(json);

      expect(mission.specialistReports, isEmpty);
    });

    test('fromJson converts priority items to strings', () {
      final json = {
        'mission_id': 'mission-005',
        'workspace_id': 'ws-111',
        'goal': 'Test priorities',
        'diagnosis': 'Test diagnosis',
        'priorities': [1, 2, 3, 'high'], // mixed types
      };

      final mission = ChiefOfStaffMission.fromJson(json);

      expect(mission.priorities.length, 4);
      expect(mission.priorities[0], '1');
      expect(mission.priorities[1], '2');
      expect(mission.priorities[3], 'high');
    });
  });
}
