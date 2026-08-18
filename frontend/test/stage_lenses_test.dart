import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/data/models/strategy_lens_model.dart';
import 'package:frontend/modules/hologram_hub/widgets/lenses/swot_evidence_grid_widget.dart';
import 'package:frontend/modules/hologram_hub/widgets/lenses/bsc_scorecard_widget.dart';

void main() {
  group('COSA Strategy Lenses Models Test', () {
    test('PestelDimension enum & parsing', () {
      expect(PestelDimension.fromString('technological'), PestelDimension.technological);
      expect(PestelDimension.fromString('economic'), PestelDimension.economic);
      expect(PestelDimension.technological.labelVi, contains('Công nghệ'));
    });

    test('SwotType enum & parsing', () {
      expect(SwotType.fromString('STRENGTH'), SwotType.strength);
      expect(SwotType.fromString('WEAKNESS'), SwotType.weakness);
      expect(SwotType.strength.labelVi, 'Điểm Mạnh (S)');
    });

    test('TowsType enum & parsing', () {
      expect(TowsType.fromString('SO'), TowsType.so);
      expect(TowsType.fromString('WT'), TowsType.wt);
    });

    test('BscPerspective enum & parsing', () {
      expect(BscPerspective.fromString('FINANCIAL'), BscPerspective.financial);
      expect(BscPerspective.fromString('CUSTOMER'), BscPerspective.customer);
    });

    test('StageLensSummaryModel deserialization from JSON', () {
      final json = {
        'project_id': 2001,
        'project_stage': 'S1_PROBLEM_VALIDATION',
        'is_bsc_unlocked': false,
        'pestel_signals': [
          {
            'id': 10,
            'workspace_id': 1001,
            'project_id': 2001,
            'dimension': 'technological',
            'signal_title': 'Local LLM nhỏ gọn',
            'description': 'Tiết kiệm chi phí',
            'impact_level': 'high',
            'time_horizon': 'short_term',
            'stage_captured': 'S1_PROBLEM_VALIDATION',
            'created_at': '2026-08-18T10:00:00Z',
          }
        ],
        'swot_items': [
          {
            'id': 20,
            'workspace_id': 1001,
            'project_id': 2001,
            'category': 'STRENGTH',
            'statement': 'Tốc độ thực thi nhanh',
            'importance': 0.9,
            'evidence_status': 'verified',
            'evidence_refs': [501],
            'created_at': '2026-08-18T10:00:00Z',
          }
        ],
        'tows_options': [
          {
            'id': 30,
            'workspace_id': 1001,
            'project_id': 2001,
            'quadrant': 'SO',
            'title': 'Gói Starter AI',
            'tradeoffs': 'Giá thấp chiếm lĩnh nhanh',
            'expected_impact': 'high',
            'confidence': 'high',
            'status': 'selected',
            'linked_strength_ids': [20],
            'tactics_12wy': [
              {
                'week_number': 1,
                'title': 'Beta test',
                'lead_indicator': '50 user feedback',
              }
            ],
            'created_at': '2026-08-18T10:00:00Z',
          }
        ],
        'bsc_goals': [],
      };

      final model = StageLensSummaryModel.fromJson(json);
      expect(model.projectId, 2001);
      expect(model.isBscUnlocked, false);
      expect(model.pestelSignals.length, 1);
      expect(model.swotItems.length, 1);
      expect(model.swotItems.first.evidenceRefs, [501]);
      expect(model.towsOptions.length, 1);
      expect(model.towsOptions.first.tactics12wy.length, 1);
    });
  });

  group('COSA Strategy Lenses Widgets Test', () {
    testWidgets('BscScorecardWidget shows locked state when isUnlocked is false', (WidgetTester tester) async {
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: BscScorecardWidget(
              isUnlocked: false,
              currentStage: 'Xác thực nỗi đau',
              bscGoals: const [],
              onCreateGoal: (_, _, _, _, _) {},
            ),
          ),
        ),
      );

      expect(find.text('Balanced Scorecard (BSC) Đang Khóa'), findsOneWidget);
      expect(find.textContaining('chỉ mở khóa từ S5'), findsOneWidget);
    });

    testWidgets('SwotEvidenceGridWidget renders 4 quadrants and evidence info', (WidgetTester tester) async {
      final swot = SwotItemModel(
        id: 20,
        workspaceId: 1001,
        projectId: 2001,
        category: SwotType.strength,
        statement: 'Tốc độ thực thi AI nhanh',
        importance: 0.85,
        evidenceStatus: 'verified',
        evidenceRefs: [501, 502],
        createdAt: DateTime.now(),
      );

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: SwotEvidenceGridWidget(
              swotItems: [swot],
              evidences: const [],
              onCreateSwotItem: (_, _, _, _) {},
            ),
          ),
        ),
      );

      expect(find.text('Điểm Mạnh (S)'), findsOneWidget);
      expect(find.text('Tốc độ thực thi AI nhanh'), findsOneWidget);
      expect(find.text('2 Bằng Chứng'), findsOneWidget);
    });
  });
}
