import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/data/models/approval_model.dart';
import 'package:frontend/modules/approvals/views/widgets/action_preview_card.dart';

void main() {
  group('COSA Lifecycle Tranche C Flow Test (Flutter)', () {
    testWidgets('Tranche C: Renders governed Bounded write approval with full audit lineage', (tester) async {
      final item = ApprovalItemModel(
        id: 'appr-c-001',
        title: 'Publish Marketing Campaign Asset (v1.2)',
        description: 'Generating optimized landing page copy based on continuous discovery evidence',
        actionClass: 'B',
        riskLevel: ApprovalRiskLevel.medium,
        skillId: 'marketing.landing-cro',
        skillHash: 'sha256_cro_asset_hash_9999',
        targetPreview: const {
          'asset_name': 'Enterprise Plan Landing Page',
          'channel': 'organic_web',
          'target_icp': 'Mid-Market SaaS CTO',
        },
        evidenceRefs: const [
          'ev-interview-102',
          'ev-hotjar-heatmaps-3',
        ],
        idempotencyKey: 'idem_cro_v12',
        rollbackPlan: 'Revert to landing page asset version 1.1',
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

      // Verify action class badge
      expect(find.textContaining('B (Bounded internal write)'), findsOneWidget);
      // Verify target preview items
      expect(find.textContaining('Enterprise Plan Landing Page'), findsOneWidget);
      expect(find.textContaining('Mid-Market SaaS CTO'), findsOneWidget);
      // Verify skill and hash
      expect(find.textContaining('marketing.landing-cro'), findsOneWidget);
      expect(find.textContaining('cro_asset_hash_9999'), findsOneWidget);
      // Verify evidence references
      expect(find.textContaining('ev-interview-102'), findsOneWidget);
      expect(find.textContaining('ev-hotjar-heatmaps-3'), findsOneWidget);
      // Verify rollback plan
      expect(find.textContaining('Revert to landing page asset version 1.1'), findsOneWidget);
    });

    testWidgets('Tranche C: Money Action (M) requires human ownership and blocks system execution', (tester) async {
      final item = ApprovalItemModel(
        id: 'appr-c-money',
        title: 'Approve Ad Spend Budget Transfer',
        actionClass: 'M',
        riskLevel: ApprovalRiskLevel.critical,
        skillId: 'finance.budget-guardrails',
        skillHash: 'sha256_budget_hash',
        status: ApprovalStatus.pending,
      );

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: ActionPreviewCard(
              item: item,
              onApprove: () {},
              onReject: () {},
            ),
          ),
        ),
      );

      expect(find.textContaining('Hành động tài chính (M): Yêu cầu con người thực hiện thủ công'), findsOneWidget);
      final elevatedBtn = tester.widget<ElevatedButton>(find.widgetWithText(ElevatedButton, 'Phê duyệt thực thi'));
      expect(elevatedBtn.onPressed, isNull);
    });
  });
}
