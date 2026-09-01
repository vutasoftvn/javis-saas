import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/modules/agents/views/widgets/agent_activity_timeline_widget.dart';
import 'package:frontend/modules/approvals/views/widgets/central_approval_inbox_widget.dart';
import 'package:frontend/modules/dashboard/views/widgets/agentic_command_center_card.dart';

// Task 3 — Nhóm test "ControlPlaneService" trước đây đã bị xoá: chúng chỉ
// kiểm chứng các route không canonical (`/agent/goals`, `/agent/runs`,
// `/agents/approvals`) mà backend thật không hề có. Hành vi thật tương
// đương giờ được kiểm chứng ở
// `frontend/test/modules/workforce/workforce_mvp_service_test.dart`. Các
// widget test render thuần từ dữ liệu truyền vào (không phụ thuộc
// ControlPlaneService) nên vẫn giữ lại nguyên trạng.
void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

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
