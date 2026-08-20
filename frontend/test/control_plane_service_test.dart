import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/core/network/api_client.dart';
import 'package:frontend/modules/mission_control/services/control_plane_service.dart';
import 'package:frontend/modules/agents/views/widgets/agent_activity_timeline_widget.dart';
import 'package:frontend/modules/approvals/views/widgets/central_approval_inbox_widget.dart';
import 'package:frontend/modules/dashboard/views/widgets/agentic_command_center_card.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  late http.Client realClient;

  setUp(() {
    realClient = ApiClient.client;
    SharedPreferences.setMockInitialValues({
      'workspace_id': '81948333752455169',
      'auth_token': 'test_token',
    });
  });

  tearDown(() {
    ApiClient.client = realClient;
  });

  group('ControlPlaneService', () {
    test('getGoals returns parsed goals list', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.url.path, '/api/v1/agent/goals');
        return http.Response(
          jsonEncode([
            {'id': '101', 'title': 'Increase pipeline', 'status': 'active'},
          ]),
          200,
        );
      });

      final goals = await ControlPlaneService().getGoals();
      expect(goals.length, 1);
      expect(goals[0]['title'], 'Increase pipeline');
    });

    test('createGoal sends JSON payload and receives parsed response', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.url.path, '/api/v1/agent/goals');
        final body = jsonDecode(request.body);
        expect(body['title'], 'New Goal');
        return http.Response(
          jsonEncode({'id': '102', 'title': 'New Goal', 'status': 'active'}),
          200,
        );
      });

      final res = await ControlPlaneService().createGoal(title: 'New Goal');
      expect(res, isNotNull);
      expect(res!['id'], '102');
    });

    test('listRuns returns parsed runs list', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.url.path, '/api/v1/agent/runs');
        return http.Response(
          jsonEncode({
            'total': 1,
            'items': [
              {'id': 'run_101', 'status': 'completed', 'agent_key': 'sales_reasoning'},
            ],
          }),
          200,
        );
      });

      final runs = await ControlPlaneService().listRuns();
      expect(runs.length, 1);
      expect(runs[0]['id'], 'run_101');
      expect(runs[0]['agent_key'], 'sales_reasoning');
    });

    test('getRunEvents returns parsed events list', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.url.path, '/api/v1/agent/runs/run_101/events');
        return http.Response(
          jsonEncode([
            {'id': 'ev_1', 'event_type': 'step_completed', 'status': 'completed'},
          ]),
          200,
        );
      });

      final events = await ControlPlaneService().getRunEvents('run_101');
      expect(events.length, 1);
      expect(events[0]['event_type'], 'step_completed');
    });

    test('approveAction sends approval request', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.url.path, '/api/v1/agents/approvals/app_123/approve');
        return http.Response(jsonEncode({'status': 'approved'}), 200);
      });

      final success = await ControlPlaneService().approveAction('app_123');
      expect(success, isTrue);
    });
  });

  group('Agentic Widgets UI Rendering', () {
    testWidgets('AgentActivityTimelineWidget renders event items', (tester) async {
      final sampleEvents = [
        {
          'domain': 'sales',
          'capability': 'research',
          'event_type': 'step_completed',
          'status': 'completed',
          'timestamp': '2026-08-15 10:00',
        },
      ];

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: AgentActivityTimelineWidget(events: sampleEvents),
          ),
        ),
      );

      expect(find.text('Agent Activity Timeline'), findsOneWidget);
      expect(find.text('sales : research'), findsOneWidget);
      expect(find.text('COMPLETED'), findsOneWidget);
    });

    testWidgets('CentralApprovalInboxWidget renders pending approvals and triggers callback', (tester) async {
      String? approvedId;
      final sampleApprovals = [
        {
          'id': 'appr_999',
          'requested_by_agent': 'sales_action',
          'action_type': 'n8n.sales.outreach_dispatch',
          'risk_level': 'medium',
        },
      ];

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: CentralApprovalInboxWidget(
              pendingApprovals: sampleApprovals,
              onApprove: (id) => approvedId = id,
            ),
          ),
        ),
      );

      expect(find.text('Central Approval Inbox'), findsOneWidget);
      expect(find.text('sales_action'), findsOneWidget);
      expect(find.text('Approve'), findsOneWidget);

      await tester.tap(find.text('Approve'));
      expect(approvedId, 'appr_999');
    });

    testWidgets('AgenticCommandCenterCard renders active goals and metrics', (tester) async {
      final sampleGoals = [
        {
          'id': 'goal_1',
          'title': 'Tăng 50 qualified leads',
          'status': 'active',
        },
      ];

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: AgenticCommandCenterCard(
              activeGoals: sampleGoals,
              pendingApprovalsCount: 1,
            ),
          ),
        ),
      );

      expect(find.text('Founder Command Center'), findsOneWidget);
      expect(find.text('Active Goals'), findsOneWidget);
      expect(find.text('Approvals Needed'), findsOneWidget);
      expect(find.text('Tăng 50 qualified leads'), findsOneWidget);
    });
  });
}
