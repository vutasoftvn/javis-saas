import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/data/models/pmf_scoreboard_model.dart';
import 'package:frontend/modules/strategy/widgets/pmf_scoreboard_panel.dart';
import 'package:frontend/modules/strategy/widgets/maturity_track_panel.dart';

void main() {
  group('PMF Scoreboard & Maturity Flutter Widgets (Task 7 / Tranche B2)', () {
    testWidgets('renders PROMISING scoreboard run with calculation hash and flags', (tester) async {
      final run = PmfScoreboardRun(
        id: 'run-101',
        workspaceId: 'ws-1',
        projectId: 'proj-1',
        policyVersion: 'v1.0',
        calculationHash: 'sha256_7f83b1657ff1fc53b92dc18148a1d65dfc2d4b1fa3d677284addd200126d9069',
        result: PmfScoreboardResult.promising,
        scoreComponents: const [
          ScoreComponent(
            componentKey: 'retention_d30',
            sourceType: 'metric_snapshot',
            sourceId: 'snap-1',
            rawScore: 0.75,
            weight: 1.0,
            weightedScore: 0.75,
            qualityStatus: 'VALID',
          ),
          ScoreComponent(
            componentKey: 'customer_interview_1',
            sourceType: 'reviewed_evidence',
            sourceId: 'ev-1',
            rawScore: 0.9,
            weight: 0.5,
            weightedScore: 0.45,
            qualityStatus: 'APPROVED',
          ),
        ],
        missingDataFlags: const [],
        reliabilityFlags: const ['STALE_SNAPSHOT:snap-9'],
        calculatedAt: DateTime.now(),
      );

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: SingleChildScrollView(
              child: PmfScoreboardPanel(run: run),
            ),
          ),
        ),
      );

      // Verify result label rendered
      expect(find.textContaining('PROMISING'), findsOneWidget);

      // Verify calculation hash rendered
      expect(find.textContaining('7f83b1657ff1fc53'), findsOneWidget);

      // Verify reliability flag rendered
      expect(find.textContaining('STALE_SNAPSHOT:snap-9'), findsOneWidget);

      // Verify component score rendered
      expect(find.text('75.0%'), findsOneWidget);
    });

    testWidgets('renders empty state when scoreboard run is null', (tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: PmfScoreboardPanel(run: null),
          ),
        ),
      );

      expect(find.text('Chưa có dữ liệu tính toán PMF Scoreboard'), findsOneWidget);
    });

    testWidgets('renders MaturityTrackPanel with 5 dimensions', (tester) async {
      final assessment = MaturityAssessment(
        id: 'mat-1',
        workspaceId: 'ws-1',
        projectId: 'proj-1',
        scoreboardRunId: 'run-101',
        measurement: const MaturityDimension(
          level: MaturityLevel.governed,
          rationale: '2 active contracts and validated scoreboard',
          missingEvidence: [],
        ),
        value: const MaturityDimension(
          level: MaturityLevel.repeatable,
          rationale: '3 approved interview evidences',
          missingEvidence: [],
        ),
        retention: const MaturityDimension(
          level: MaturityLevel.early,
          rationale: 'Initial cohort data only',
          missingEvidence: ['Missing day 60 retention snapshot'],
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
        assessedAt: DateTime.now(),
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

      expect(find.textContaining('Ma Trận Trưởng Thành PMF'), findsOneWidget);
      expect(find.textContaining('1. Đo lường & Hợp đồng chỉ số'), findsOneWidget);
      expect(find.textContaining('2. Giá trị khách hàng xác thực'), findsOneWidget);
      expect(find.textContaining('3. Tỷ lệ gắn kết & Giữ chân'), findsOneWidget);
      expect(find.textContaining('4. Sự sẵn sàng thương mại'), findsOneWidget);
      expect(find.textContaining('5. Năng lực vận hành học hỏi'), findsOneWidget);

      expect(find.textContaining('GOVERNED'), findsOneWidget);
      expect(find.textContaining('REPEATABLE'), findsWidgets);
      expect(find.textContaining('EARLY'), findsOneWidget);
      expect(find.textContaining('NOT ASSESSED'), findsOneWidget);
    });
  });
}
