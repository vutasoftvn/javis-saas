import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/data/models/pilot_run_model.dart';
import 'package:frontend/modules/strategy/views/widgets/pilot_readiness_panel.dart';

void main() {
  group('PilotReadinessPanel Widget Tests', () {
    testWidgets('does not show activate until approved and every required reference exists', (WidgetTester tester) async {
      final draftMissingRollback = PilotRun(
        id: '101',
        workspaceId: '1001',
        projectId: '2001',
        status: PilotRunStatus.draft,
        designPartnerEvidenceRefs: ['3001'],
        metricContractArtifactRef: 'artifact://ws/metrics',
        instrumentationArtifactRef: 'artifact://ws/inst',
        onboardingArtifactRef: 'artifact://ws/onb',
        rollbackArtifactRef: null, // MISSING
        releaseOwnerMemberId: '9001',
        version: 1,
        createdAt: DateTime.now(),
        updatedAt: DateTime.now(),
      );

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: SingleChildScrollView(
              child: PilotReadinessPanel(
                pilot: draftMissingRollback,
                isFounderOrAdmin: true,
              ),
            ),
          ),
        ),
      );

      // Explicitly renders missing item
      expect(find.textContaining('Thiếu rollback runbook'), findsOneWidget);
      // Does NOT show activate button
      expect(find.text('Kích hoạt pilot'), findsNothing);
      // Shows explanatory invariant banner
      expect(find.textContaining('Kích hoạt pilot không thay đổi lifecycle stage'), findsOneWidget);
    });

    testWidgets('shows activate button only when pilot is APPROVED and user has permission', (WidgetTester tester) async {
      final approvedPilot = PilotRun(
        id: '102',
        workspaceId: '1001',
        projectId: '2001',
        status: PilotRunStatus.approved,
        designPartnerEvidenceRefs: ['3001'],
        metricContractArtifactRef: 'artifact://ws/metrics',
        instrumentationArtifactRef: 'artifact://ws/inst',
        onboardingArtifactRef: 'artifact://ws/onb',
        rollbackArtifactRef: 'artifact://ws/rb',
        releaseOwnerMemberId: '9001',
        approvalRef: 'APR-2026-001',
        approvedAt: DateTime.now(),
        version: 2,
        createdAt: DateTime.now(),
        updatedAt: DateTime.now(),
      );

      String? activatedRef;

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: SingleChildScrollView(
              child: PilotReadinessPanel(
                pilot: approvedPilot,
                isFounderOrAdmin: true,
                onActivate: (ref) {
                  activatedRef = ref;
                },
              ),
            ),
          ),
        ),
      );

      expect(find.text('Kích hoạt pilot'), findsOneWidget);
      expect(find.textContaining('APR-2026-001'), findsOneWidget);

      // Tap activate button
      await tester.tap(find.text('Kích hoạt pilot'));
      await tester.pumpAndSettle();

      // Dialog opens requesting approval reference
      expect(find.text('Kích Hoạt Pilot (Human Authorization)'), findsOneWidget);
      expect(find.text('Xác nhận Kích hoạt'), findsOneWidget);

      // Enter approval ref and submit
      await tester.enterText(find.byType(TextField), 'APR-FOUNDER-99');
      await tester.tap(find.text('Xác nhận Kích hoạt'));
      await tester.pumpAndSettle();

      expect(activatedRef, 'APR-FOUNDER-99');
    });
  });
}
