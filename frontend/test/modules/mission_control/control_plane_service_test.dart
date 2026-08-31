import 'dart:convert';
import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/core/network/api_client.dart';
import 'package:frontend/modules/mission_control/services/control_plane_service.dart';
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

  group('ControlPlaneService.getGoals', () {
    test('fetches all goals successfully', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.method, 'GET');
        expect(request.url.path, '/agent/goals');
        return http.Response(
          jsonEncode([
            {'id': 'goal-001', 'title': 'Goal 1', 'status': 'active'},
            {'id': 'goal-002', 'title': 'Goal 2', 'status': 'completed'},
          ]),
          200,
        );
      });

      final service = ControlPlaneService();
      final goals = await service.getGoals();

      expect(goals.length, 2);
      expect(goals[0]['id'], 'goal-001');
      expect(goals[1]['title'], 'Goal 2');
    });

    test('fetches goals with status filter', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.url.queryParameters['status'], 'active');
        return http.Response(
          jsonEncode([
            {'id': 'goal-001', 'status': 'active'},
          ]),
          200,
        );
      });

      final service = ControlPlaneService();
      final goals = await service.getGoals(status: 'active');

      expect(goals.length, 1);
      expect(goals[0]['status'], 'active');
    });

    test('returns empty list on 404', () async {
      ApiClient.client = MockClient((request) async {
        return http.Response('Not found', 404);
      });

      final service = ControlPlaneService();
      final goals = await service.getGoals();

      expect(goals, isEmpty);
    });

    test('returns empty list on 500', () async {
      ApiClient.client = MockClient((request) async {
        return http.Response('Server error', 500);
      });

      final service = ControlPlaneService();
      final goals = await service.getGoals();

      expect(goals, isEmpty);
    });
  });

  group('ControlPlaneService.createGoal', () {
    test('creates goal with required fields', () async {
      String? capturedBody;
      ApiClient.client = MockClient((request) async {
        expect(request.method, 'POST');
        expect(request.url.path, '/agent/goals');
        capturedBody = request.body;
        return http.Response(
          jsonEncode({
            'id': 'goal-new-001',
            'title': 'New Goal',
            'status': 'created',
          }),
          200,
        );
      });

      final service = ControlPlaneService();
      final goal = await service.createGoal(title: 'New Goal');

      expect(goal, isNotNull);
      expect(goal!['id'], 'goal-new-001');

      final body = jsonDecode(capturedBody!) as Map<String, dynamic>;
      expect(body['title'], 'New Goal');
      expect(body['goal_type'], 'business_goal');
      expect(body['auto_plan'], isTrue);
    });

    test('creates goal with all optional parameters', () async {
      String? capturedBody;
      ApiClient.client = MockClient((request) async {
        capturedBody = request.body;
        return http.Response(
          jsonEncode({'id': 'goal-new', 'status': 'created'}),
          200,
        );
      });

      final service = ControlPlaneService();
      final goal = await service.createGoal(
        title: 'Revenue Goal',
        description: 'Increase revenue by 50%',
        goalType: 'revenue_goal',
        targetMetric: {'currency': 'USD', 'amount': 1000000},
        autoPlan: false,
        domainHint: 'sales',
      );

      expect(goal, isNotNull);

      final body = jsonDecode(capturedBody!) as Map<String, dynamic>;
      expect(body['title'], 'Revenue Goal');
      expect(body['description'], 'Increase revenue by 50%');
      expect(body['goal_type'], 'revenue_goal');
      expect(body['target_metric']['amount'], 1000000);
      expect(body['auto_plan'], isFalse);
      expect(body['domain_hint'], 'sales');
    });

    test('returns null on non-200 status', () async {
      ApiClient.client = MockClient((request) async {
        return http.Response('Error', 400);
      });

      final service = ControlPlaneService();
      final goal = await service.createGoal(title: 'Test');

      expect(goal, isNull);
    });
  });

  group('ControlPlaneService.getPlan', () {
    test('fetches plan successfully', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.url.path, '/agent/plans/plan-123');
        return http.Response(
          jsonEncode({
            'id': 'plan-123',
            'steps': [
              {'step': 1, 'description': 'Step 1'},
            ],
          }),
          200,
        );
      });

      final service = ControlPlaneService();
      final plan = await service.getPlan('plan-123');

      expect(plan, isNotNull);
      expect(plan!['id'], 'plan-123');
      expect((plan['steps'] as List).length, 1);
    });

    test('returns null on 404', () async {
      ApiClient.client = MockClient((request) async {
        return http.Response('Not found', 404);
      });

      final service = ControlPlaneService();
      final plan = await service.getPlan('nonexistent-plan');

      expect(plan, isNull);
    });
  });

  group('ControlPlaneService.executePlanStep', () {
    test('executes next step without step ID', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.method, 'POST');
        expect(request.url.path, '/agent/plans/plan-123/execute-step');
        expect(request.url.queryParameters['step_id'], isNull);
        return http.Response(
          jsonEncode({'step': 1, 'status': 'executed'}),
          200,
        );
      });

      final service = ControlPlaneService();
      final result = await service.executePlanStep('plan-123');

      expect(result, isNotNull);
      expect(result!['status'], 'executed');
    });

    test('executes specific step with step ID', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.url.queryParameters['step_id'], 'step-5');
        return http.Response(
          jsonEncode({'step': 5, 'status': 'executed'}),
          200,
        );
      });

      final service = ControlPlaneService();
      final result = await service.executePlanStep('plan-123', stepId: 'step-5');

      expect(result, isNotNull);
      expect(result!['step'], 5);
    });

    test('returns null on 500', () async {
      ApiClient.client = MockClient((request) async {
        return http.Response('Server error', 500);
      });

      final service = ControlPlaneService();
      final result = await service.executePlanStep('plan-123');

      expect(result, isNull);
    });
  });

  group('ControlPlaneService.listRuns', () {
    test('lists runs with default pagination', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.url.queryParameters['limit'], '20');
        expect(request.url.queryParameters['offset'], '0');
        return http.Response(
          jsonEncode([
            {'id': 'run-001', 'status': 'completed'},
            {'id': 'run-002', 'status': 'running'},
          ]),
          200,
        );
      });

      final service = ControlPlaneService();
      final runs = await service.listRuns();

      expect(runs.length, 2);
      expect(runs[0]['id'], 'run-001');
    });

    test('lists runs with status filter', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.url.queryParameters['status'], 'running');
        return http.Response(
          jsonEncode([
            {'id': 'run-002', 'status': 'running'},
          ]),
          200,
        );
      });

      final service = ControlPlaneService();
      final runs = await service.listRuns(status: 'running');

      expect(runs.length, 1);
      expect(runs[0]['status'], 'running');
    });

    test('lists runs with custom pagination', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.url.queryParameters['limit'], '50');
        expect(request.url.queryParameters['offset'], '100');
        return http.Response(jsonEncode([]), 200);
      });

      final service = ControlPlaneService();
      await service.listRuns(limit: 50, offset: 100);
    });

    test('handles map response with items key', () async {
      ApiClient.client = MockClient((request) async {
        return http.Response(
          jsonEncode({
            'items': [
              {'id': 'run-001'},
              {'id': 'run-002'},
            ],
            'total': 2,
          }),
          200,
        );
      });

      final service = ControlPlaneService();
      final runs = await service.listRuns();

      expect(runs.length, 2);
      expect(runs[0]['id'], 'run-001');
    });

    test('handles array response format', () async {
      ApiClient.client = MockClient((request) async {
        return http.Response(
          jsonEncode([
            {'id': 'run-001'},
            {'id': 'run-002'},
          ]),
          200,
        );
      });

      final service = ControlPlaneService();
      final runs = await service.listRuns();

      expect(runs.length, 2);
    });

    test('returns empty list on error', () async {
      ApiClient.client = MockClient((request) async {
        return http.Response('Error', 500);
      });

      final service = ControlPlaneService();
      final runs = await service.listRuns();

      expect(runs, isEmpty);
    });
  });

  group('ControlPlaneService.getRunEvents', () {
    test('fetches run events successfully', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.url.path, '/agent/runs/run-123/events');
        return http.Response(
          jsonEncode([
            {'event_id': 'evt-001', 'type': 'started'},
            {'event_id': 'evt-002', 'type': 'completed'},
          ]),
          200,
        );
      });

      final service = ControlPlaneService();
      final events = await service.getRunEvents('run-123');

      expect(events.length, 2);
      expect(events[0]['event_id'], 'evt-001');
    });

    test('returns empty list on 404', () async {
      ApiClient.client = MockClient((request) async {
        return http.Response('Not found', 404);
      });

      final service = ControlPlaneService();
      final events = await service.getRunEvents('nonexistent-run');

      expect(events, isEmpty);
    });
  });

  group('ControlPlaneService.getPendingApprovals', () {
    test('fetches pending approvals successfully', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.url.path, '/agents/approvals');
        return http.Response(
          jsonEncode([
            {'id': 'app-001', 'action': 'approve_action_1'},
            {'id': 'app-002', 'action': 'approve_action_2'},
          ]),
          200,
        );
      });

      final service = ControlPlaneService();
      final approvals = await service.getPendingApprovals();

      expect(approvals.length, 2);
      expect(approvals[0]['id'], 'app-001');
    });

    test('returns empty list when no approvals', () async {
      ApiClient.client = MockClient((request) async {
        return http.Response(jsonEncode([]), 200);
      });

      final service = ControlPlaneService();
      final approvals = await service.getPendingApprovals();

      expect(approvals, isEmpty);
    });

    test('returns empty list on error', () async {
      ApiClient.client = MockClient((request) async {
        return http.Response('Error', 500);
      });

      final service = ControlPlaneService();
      final approvals = await service.getPendingApprovals();

      expect(approvals, isEmpty);
    });
  });

  group('ControlPlaneService.approveAction', () {
    test('approves action successfully', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.method, 'POST');
        expect(request.url.path, '/agents/approvals/app-123/approve');
        return http.Response(jsonEncode({'status': 'approved'}), 200);
      });

      final service = ControlPlaneService();
      final ok = await service.approveAction('app-123');

      expect(ok, isTrue);
    });

    test('includes reason in request body when provided', () async {
      String? capturedBody;
      ApiClient.client = MockClient((request) async {
        capturedBody = request.body;
        return http.Response(jsonEncode({}), 200);
      });

      final service = ControlPlaneService();
      await service.approveAction('app-123', reason: 'All checks passed');

      final body = jsonDecode(capturedBody!) as Map<String, dynamic>;
      expect(body['reason'], 'All checks passed');
    });

    test('returns false on non-200 status', () async {
      ApiClient.client = MockClient((request) async {
        return http.Response('Error', 400);
      });

      final service = ControlPlaneService();
      final ok = await service.approveAction('app-999');

      expect(ok, isFalse);
    });
  });

  group('ControlPlaneService.rejectAction', () {
    test('rejects action successfully', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.method, 'POST');
        expect(request.url.path, '/agents/approvals/app-456/reject');
        return http.Response(jsonEncode({'status': 'rejected'}), 200);
      });

      final service = ControlPlaneService();
      final ok = await service.rejectAction('app-456');

      expect(ok, isTrue);
    });

    test('includes reason in request body when provided', () async {
      String? capturedBody;
      ApiClient.client = MockClient((request) async {
        capturedBody = request.body;
        return http.Response(jsonEncode({}), 200);
      });

      final service = ControlPlaneService();
      await service.rejectAction('app-456', reason: 'Needs more review');

      final body = jsonDecode(capturedBody!) as Map<String, dynamic>;
      expect(body['reason'], 'Needs more review');
    });

    test('returns false on 401', () async {
      ApiClient.client = MockClient((request) async {
        return http.Response('Unauthorized', 401);
      });

      final service = ControlPlaneService();
      final ok = await service.rejectAction('app-999');

      expect(ok, isFalse);
    });
  });
}
