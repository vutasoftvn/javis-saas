import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/data/models/evidence_model.dart';
import 'package:frontend/shared/widgets/evidence_ladder_badge.dart';
import 'package:frontend/modules/hologram_hub/widgets/evidence/hypothesis_card.dart';
import 'package:frontend/modules/hologram_hub/widgets/evidence/evidence_item_card.dart';

void main() {
  group('COSA Evidence Core Models Test', () {
    test('EvidenceLadderLevel Enum parsing, weights & codes', () {
      expect(EvidenceLadderLevel.fromString('E0_OPINION'), EvidenceLadderLevel.e0Opinion);
      expect(EvidenceLadderLevel.fromString('E1_STATED_INTEREST'), EvidenceLadderLevel.e1StatedInterest);
      expect(EvidenceLadderLevel.fromString('E2_OBSERVED_PROBLEM'), EvidenceLadderLevel.e2ObservedProblem);
      expect(EvidenceLadderLevel.fromString('E3_BEHAVIORAL_COMMITMENT'), EvidenceLadderLevel.e3BehavioralCommitment);
      expect(EvidenceLadderLevel.fromString('E4_ECONOMIC_COMMITMENT'), EvidenceLadderLevel.e4EconomicCommitment);
      expect(EvidenceLadderLevel.fromString('E5_REPEAT_BEHAVIOR'), EvidenceLadderLevel.e5RepeatBehavior);
      expect(EvidenceLadderLevel.fromString('E6_SCALABLE_EVIDENCE'), EvidenceLadderLevel.e6ScalableEvidence);

      expect(EvidenceLadderLevel.e0Opinion.weight, 0.0);
      expect(EvidenceLadderLevel.e1StatedInterest.weight, 0.2);
      expect(EvidenceLadderLevel.e4EconomicCommitment.weight, 0.9);
      expect(EvidenceLadderLevel.e6ScalableEvidence.weight, 1.0);
      expect(EvidenceLadderLevel.e4EconomicCommitment.code, 'E4');
    });

    test('HypothesisModel deserialization from JSON', () {
      final json = {
        'id': 101,
        'workspace_id': 1001,
        'project_id': 2001,
        'category': 'pricing',
        'statement': 'Khách hàng sẵn sàng trả 500k/tháng',
        'importance': 0.9,
        'uncertainty': 0.8,
        'risk_score': 0.72,
        'evidence_score': 0.85,
        'confidence': 0.75,
        'status': 'SUPPORTED',
        'stage_created': 'S2_SOLUTION_VALIDATION',
        'evidence_refs': [501, 502],
        'experiment_refs': [],
        'next_action': 'Tăng giá lên 700k',
        'created_at': '2026-08-18T10:00:00Z',
        'updated_at': '2026-08-18T10:00:00Z',
      };

      final model = HypothesisModel.fromJson(json);

      expect(model.id, 101);
      expect(model.category, 'pricing');
      expect(model.riskScore, 0.72);
      expect(model.evidenceScore, 0.85);
      expect(model.status, HypothesisStatus.supported);
      expect(model.evidenceRefs.length, 2);
    });

    test('EvidenceModel deserialization from JSON', () {
      final json = {
        'id': 501,
        'workspace_id': 1001,
        'project_id': 2001,
        'type': 'transaction',
        'ladder_level': 'E4_ECONOMIC_COMMITMENT',
        'ladder_weight': 0.9,
        'source': 'Stripe Invoice #102',
        'claim_supported': 'Khách hàng thanh toán trước 1 năm',
        'strength': 'strong',
        'direction': 'supports',
        'hypothesis_refs': [101],
        'artifact_refs': [],
        'raw_payload': {'amount': 6000000},
        'captured_at': '2026-08-18T10:00:00Z',
        'created_at': '2026-08-18T10:00:00Z',
      };

      final model = EvidenceModel.fromJson(json);

      expect(model.id, 501);
      expect(model.ladderLevel, EvidenceLadderLevel.e4EconomicCommitment);
      expect(model.direction, 'supports');
      expect(model.strength, 'strong');
      expect(model.rawPayload['amount'], 6000000);
    });
  });

  group('COSA Evidence Core Widgets Test', () {
    testWidgets('EvidenceLadderBadge renders correctly', (WidgetTester tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: Center(
              child: EvidenceLadderBadge(
                level: EvidenceLadderLevel.e4EconomicCommitment,
                showFullTitle: true,
              ),
            ),
          ),
        ),
      );

      expect(find.text('E4'), findsOneWidget);
      expect(find.textContaining('Trả tiền thật'), findsOneWidget);
    });

    testWidgets('HypothesisCard renders statement and Evidence Score %', (WidgetTester tester) async {
      final hypo = HypothesisModel(
        id: 101,
        workspaceId: 1001,
        projectId: 2001,
        category: 'pricing',
        statement: 'Khách hàng sẵn sàng trả 500k/tháng',
        importance: 0.9,
        uncertainty: 0.8,
        riskScore: 0.72,
        evidenceScore: 0.85,
        confidence: 0.75,
        status: HypothesisStatus.supported,
        stageCreated: 'S2_SOLUTION_VALIDATION',
        evidenceRefs: [501, 502],
        experimentRefs: [],
        createdAt: DateTime.now(),
        updatedAt: DateTime.now(),
      );

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: HypothesisCard(
              hypothesis: hypo,
            ),
          ),
        ),
      );

      expect(find.text('Khách hàng sẵn sàng trả 500k/tháng'), findsOneWidget);
      expect(find.text('85%'), findsOneWidget);
      expect(find.text('72%'), findsOneWidget);
      expect(find.text('RỦI RO SỐNG CÒN'), findsOneWidget);
      expect(find.text('Đã xác thực (Passed)'), findsOneWidget);
    });

    testWidgets('EvidenceItemCard renders claim and source', (WidgetTester tester) async {
      final ev = EvidenceModel(
        id: 501,
        workspaceId: 1001,
        projectId: 2001,
        type: 'transaction',
        ladderLevel: EvidenceLadderLevel.e4EconomicCommitment,
        ladderWeight: 0.9,
        source: 'Stripe Invoice #102',
        claimSupported: 'Khách hàng thanh toán trước 1 năm',
        strength: 'strong',
        direction: 'supports',
        hypothesisRefs: [101],
        artifactRefs: [],
        rawPayload: {},
        capturedAt: DateTime.now(),
        createdAt: DateTime.now(),
      );

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: EvidenceItemCard(
              evidence: ev,
            ),
          ),
        ),
      );

      expect(find.text('Khách hàng thanh toán trước 1 năm'), findsOneWidget);
      expect(find.text('Stripe Invoice #102'), findsOneWidget);
      expect(find.text('Ủng Hộ (+)'), findsOneWidget);
      expect(find.text('E4'), findsOneWidget);
    });
  });
}
