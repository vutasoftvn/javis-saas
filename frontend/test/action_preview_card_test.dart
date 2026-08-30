import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/data/models/approval_model.dart';
import 'package:frontend/modules/approvals/views/widgets/action_preview_card.dart';

void main() {
  group('ActionPreviewCard Widget Tests (Tranche C / Task 3)', () {
    testWidgets('renders Bounded write (B) with target preview, skill hash, and evidence refs', (tester) async {
      final item = ApprovalItemModel(
        id: 'appr-101',
        title: 'Draft Operations Task: Fix Webhook',
        description: 'Creating high-priority task based on metric anomaly',
        actionClass: 'B',
        skillId: 'operations.task-manager',
        skillHash: 'sha256_abcdef1234567890',
        targetPreview: const {
          'project_id': 'proj-alpha',
          'priority': 'high',
          'assigned_to': 'eng-lead',
        },
        evidenceRefs: const ['ev-metric-anomaly-1', 'ev-slack-alert-2'],
        idempotencyKey: 'idem_ops_task_001',
        rollbackPlan: 'Delete draft task via DELETE /operations/tasks/101',
        status: ApprovalStatus.pending,
      );

      bool approved = false;
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: SingleChildScrollView(
              child: ActionPreviewCard(
                item: item,
                onApprove: () => approved = true,
                onReject: () {},
              ),
            ),
          ),
        ),
      );

      expect(find.textContaining('B (Bounded internal write)'), findsOneWidget);
      expect(find.text('Draft Operations Task: Fix Webhook'), findsOneWidget);
      expect(find.textContaining('• project_id: proj-alpha'), findsOneWidget);
      expect(find.textContaining('Skill: operations.task-manager'), findsOneWidget);
      expect(find.textContaining('ev-metric-anomaly-1'), findsOneWidget);
      expect(find.textContaining('Idempotency: idem_ops_task_001'), findsOneWidget);

      // Verify approve button is enabled and clickable
      final approveBtn = find.widgetWithText(ElevatedButton, 'Phê duyệt thực thi');
      expect(approveBtn, findsOneWidget);
      await tester.tap(approveBtn);
      expect(approved, isTrue);
    });

    testWidgets('Action Class M (Money/Human-owned) disables direct execution', (tester) async {
      final item = ApprovalItemModel(
        id: 'appr-m-001',
        title: 'Payout Vendor Invoice #502',
        actionClass: 'M',
        skillId: 'finance.unit-economics',
        skillHash: 'sha256_fin_hash_123',
        status: ApprovalStatus.pending,
      );

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: SingleChildScrollView(
              child: ActionPreviewCard(
                item: item,
                onApprove: () {},
                onReject: () {},
              ),
            ),
          ),
        ),
      );

      expect(find.textContaining('M (Money / Human-owned)'), findsOneWidget);
      expect(find.textContaining('Hành động tài chính (M): Yêu cầu con người thực hiện thủ công'), findsOneWidget);

      // Approve button must be disabled (onPressed is null)
      final elevatedBtn = tester.widget<ElevatedButton>(find.widgetWithText(ElevatedButton, 'Phê duyệt thực thi'));
      expect(elevatedBtn.onPressed, isNull);
    });

    testWidgets('Expired approval displays warning and disables execution', (tester) async {
      final item = ApprovalItemModel(
        id: 'appr-exp-001',
        title: 'Campaign Asset Deployment',
        actionClass: 'B',
        skillId: 'marketing.landing-cro',
        skillHash: 'sha256_cro_hash',
        expiresAt: DateTime.now().subtract(const Duration(hours: 2)),
        status: ApprovalStatus.pending,
      );

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: SingleChildScrollView(
              child: ActionPreviewCard(
                item: item,
                onApprove: () {},
                onReject: () {},
              ),
            ),
          ),
        ),
      );

      expect(find.textContaining('Yêu cầu đã hết hạn phê duyệt'), findsOneWidget);
      final elevatedBtn = tester.widget<ElevatedButton>(find.widgetWithText(ElevatedButton, 'Phê duyệt thực thi'));
      expect(elevatedBtn.onPressed, isNull);
    });

    testWidgets('Invalid / missing skill hash displays blocked state', (tester) async {
      final item = ApprovalItemModel(
        id: 'appr-bad-hash',
        title: 'Unverified Skill Execution',
        actionClass: 'B',
        skillId: 'unverified.skill',
        skillHash: '',
        status: ApprovalStatus.pending,
      );

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: SingleChildScrollView(
              child: ActionPreviewCard(
                item: item,
                onApprove: () {},
                onReject: () {},
              ),
            ),
          ),
        ),
      );

      expect(find.textContaining('Skill hash không xác định - Chặn thực thi'), findsOneWidget);
      final elevatedBtn = tester.widget<ElevatedButton>(find.widgetWithText(ElevatedButton, 'Phê duyệt thực thi'));
      expect(elevatedBtn.onPressed, isNull);
    });
  });
}
