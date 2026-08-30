// Task 7 gap-fill (Tranche B2 audit) — widget test riêng cho MaturityTrackPanel
// (trước đây chỉ được phủ gián tiếp qua pmf_scoreboard_panel_test.dart).
// Đảm bảo cả 5 dimension trưởng thành render đúng status + rationale, và
// trạng thái NOT_ASSESSED không bao giờ hiện màu xanh/green "pass" treatment.
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/data/models/pmf_scoreboard_model.dart';
import 'package:frontend/modules/strategy/widgets/maturity_track_panel.dart';

void main() {
  group('MaturityTrackPanel', () {
    testWidgets('renders empty state when assessment is null', (tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: MaturityTrackPanel(assessment: null),
          ),
        ),
      );

      expect(find.textContaining('Chưa có Đánh Giá Trưởng Thành'), findsOneWidget);
    });

    testWidgets('renders loading state', (tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: MaturityTrackPanel(assessment: null, isLoading: true),
          ),
        ),
      );

      expect(find.byType(CircularProgressIndicator), findsOneWidget);
    });

    testWidgets('renders each of the 5 maturity dimensions with status and rationale', (tester) async {
      final assessment = MaturityAssessment(
        id: 'mat-1',
        workspaceId: 'ws-1',
        projectId: 'proj-1',
        scoreboardRunId: 'run-101',
        measurement: const MaturityDimension(
          level: MaturityLevel.governed,
          rationale: 'Two active metric contracts wired end to end',
          missingEvidence: [],
        ),
        value: const MaturityDimension(
          level: MaturityLevel.repeatable,
          rationale: 'Three approved interview evidences confirm value',
          missingEvidence: [],
        ),
        retention: const MaturityDimension(
          level: MaturityLevel.early,
          rationale: 'Only one cohort observed so far',
          missingEvidence: ['Missing day-60 retention snapshot'],
        ),
        commercial: const MaturityDimension(
          level: MaturityLevel.notAssessed,
          rationale: 'No commercial pilot outcome recorded yet',
          missingEvidence: ['Missing LOI or pilot payment receipt'],
        ),
        operational: const MaturityDimension(
          level: MaturityLevel.repeatable,
          rationale: 'Continuous evidence collection process in place',
          missingEvidence: [],
        ),
        assessedAt: DateTime(2026, 8, 30),
      );

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: SingleChildScrollView(
              child: MaturityTrackPanel(assessment: assessment),
            ),
          ),
        ),
      );

      // 5 dimension titles rendered.
      expect(find.textContaining('1. Đo lường & Hợp đồng chỉ số'), findsOneWidget);
      expect(find.textContaining('2. Giá trị khách hàng xác thực'), findsOneWidget);
      expect(find.textContaining('3. Tỷ lệ gắn kết & Giữ chân'), findsOneWidget);
      expect(find.textContaining('4. Sự sẵn sàng thương mại'), findsOneWidget);
      expect(find.textContaining('5. Năng lực vận hành học hỏi'), findsOneWidget);

      // Status labels rendered for each dimension.
      expect(find.textContaining('GOVERNED'), findsOneWidget);
      expect(find.textContaining('REPEATABLE'), findsNWidgets(2));
      expect(find.textContaining('EARLY'), findsOneWidget);
      expect(find.textContaining('NOT ASSESSED'), findsOneWidget);

      // Rationale text rendered for each dimension (tiles start expanded via ExpansionTile
      // default state — ensureVisible not required since ExpansionTile renders children lazily
      // only when expanded; tap each tile open to assert rationale content).
      await tester.tap(find.textContaining('1. Đo lường & Hợp đồng chỉ số'));
      await tester.pumpAndSettle();
      expect(find.textContaining('Two active metric contracts wired end to end'), findsOneWidget);

      await tester.tap(find.textContaining('3. Tỷ lệ gắn kết & Giữ chân'));
      await tester.pumpAndSettle();
      expect(find.textContaining('Only one cohort observed so far'), findsOneWidget);
      expect(find.textContaining('Missing day-60 retention snapshot'), findsOneWidget);

      await tester.tap(find.textContaining('4. Sự sẵn sàng thương mại'));
      await tester.pumpAndSettle();
      expect(find.textContaining('No commercial pilot outcome recorded yet'), findsOneWidget);
      expect(find.textContaining('Missing LOI or pilot payment receipt'), findsOneWidget);
    });

    testWidgets('NOT_ASSESSED dimension never renders green/success color treatment', (tester) async {
      final assessment = MaturityAssessment(
        id: 'mat-2',
        workspaceId: 'ws-1',
        projectId: 'proj-1',
        measurement: const MaturityDimension(level: MaturityLevel.notAssessed, rationale: 'No data yet'),
        value: const MaturityDimension(level: MaturityLevel.notAssessed, rationale: 'No data yet'),
        retention: const MaturityDimension(level: MaturityLevel.notAssessed, rationale: 'No data yet'),
        commercial: const MaturityDimension(level: MaturityLevel.notAssessed, rationale: 'No data yet'),
        operational: const MaturityDimension(level: MaturityLevel.notAssessed, rationale: 'No data yet'),
        assessedAt: DateTime(2026, 8, 30),
      );

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: SingleChildScrollView(
              child: MaturityTrackPanel(assessment: assessment),
            ),
          ),
        ),
      );

      // All 5 badges must read NOT ASSESSED — no GOVERNED/REPEATABLE/EARLY green label leaking through.
      expect(find.textContaining('NOT ASSESSED'), findsNWidgets(5));
      expect(find.textContaining('GOVERNED'), findsNothing);

      // The badge container color for every ExpansionTile must not be Colors.green —
      // the widget's own _getLevelColor maps notAssessed/unknown to Colors.grey.
      final containers = tester.widgetList<Container>(find.byType(Container));
      for (final container in containers) {
        final decoration = container.decoration;
        if (decoration is BoxDecoration && decoration.color != null) {
          expect(
            decoration.color,
            isNot(Colors.green.withOpacity(0.12)),
            reason: 'NOT_ASSESSED dimension must not render the green "pass" badge treatment',
          );
        }
      }

      // Every leading icon for NOT_ASSESSED dimensions must be grey, never green.
      final icons = tester.widgetList<Icon>(find.byType(Icon));
      for (final icon in icons) {
        expect(icon.color, isNot(Colors.green), reason: 'NOT_ASSESSED icon must not be rendered green');
      }
    });
  });
}
