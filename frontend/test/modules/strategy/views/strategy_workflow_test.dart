import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/modules/strategy/models/strategy_workflow_models.dart';
import 'package:frontend/modules/strategy/views/tabs/strategy_lenses_tab.dart';
import 'package:frontend/modules/strategy/widgets/bsc_focus_scope_step.dart';
import 'package:frontend/modules/strategy/widgets/strategy_analysis_step.dart';
import 'package:frontend/modules/strategy/widgets/tows_prioritization_step.dart';

Future<void> _pumpApp(WidgetTester tester, Widget child, {Size size = const Size(1280, 900)}) async {
  tester.view.physicalSize = size;
  tester.view.devicePixelRatio = 1.0;
  tester.binding.addPostFrameCallback((_) {});
  addTearDown(() {
    tester.view.resetPhysicalSize();
    tester.view.resetDevicePixelRatio();
  });
  await tester.pumpWidget(
    MaterialApp(
      home: Scaffold(
        body: child,
      ),
    ),
  );
  await tester.pumpAndSettle();
}

void main() {
  final sampleObjective = StrategicObjectiveModel(
    id: 'obj_101',
    workspaceId: 'ws_1',
    title: 'Trở thành nền tảng AI SaaS số 1 VN',
    successDefinition: 'Đạt 1,000 khách hàng trả phí ARR 1M USD',
    timeHorizonEnd: '2027-12-31',
    status: 'ACTIVE',
    revision: 1,
  );

  group('Strategy Workflow Guided Steps & Policy Governance Tests', () {
    testWidgets('1. BSC OFF allows skipping BSC step without blocking', (tester) async {
      final settings = WorkspaceStrategySettingsModel(
        workspaceId: 'ws_1',
        strategyMethod: StrategyMethod.bscFilter,
        bscMode: BscMode.off,
        maxTowsSelections: 2,
      );

      bool nextCalled = false;

      await _pumpApp(
        tester,
        BscFocusScopeStep(
          selectedObjective: sampleObjective,
          settings: settings,
          focusScopes: const [],
          onSaveFocusScopes: (_) async {},
          onNext: () => nextCalled = true,
          onBack: () {},
        ),
      );

      // Expect notice that BSC is disabled
      expect(find.textContaining('Chế độ BSC đang TẮT'), findsOneWidget);

      // Verify skip button is available and clickable
      final skipBtn = find.byKey(const Key('btn_bsc_skip'));
      expect(skipBtn, findsOneWidget);
      await tester.tap(skipBtn);
      await tester.pumpAndSettle();

      expect(nextCalled, isTrue);
    });

    testWidgets('2. BSC OPTIONAL allows skipping when no scopes defined', (tester) async {
      final settings = WorkspaceStrategySettingsModel(
        workspaceId: 'ws_1',
        strategyMethod: StrategyMethod.bscFilter,
        bscMode: BscMode.optional,
        maxTowsSelections: 2,
      );

      bool nextCalled = false;

      await _pumpApp(
        tester,
        BscFocusScopeStep(
          selectedObjective: sampleObjective,
          settings: settings,
          focusScopes: const [],
          onSaveFocusScopes: (_) async {},
          onNext: () => nextCalled = true,
          onBack: () {},
        ),
      );

      expect(find.textContaining('Chế độ BSC TÙY CHỌN'), findsOneWidget);

      final nextBtn = find.byKey(const Key('btn_next_step'));
      expect(nextBtn, findsOneWidget);
      await tester.tap(nextBtn);
      await tester.pumpAndSettle();

      expect(nextCalled, isTrue);
    });

    testWidgets('3. BSC REQUIRED blocks proceeding when 0 scopes exist, proceeds when >=1 scope exists', (tester) async {
      final settings = WorkspaceStrategySettingsModel(
        workspaceId: 'ws_1',
        strategyMethod: StrategyMethod.bscFilter,
        bscMode: BscMode.required,
        maxTowsSelections: 2,
      );

      bool nextCalled = false;

      // When 0 scopes exist
      await _pumpApp(
        tester,
        BscFocusScopeStep(
          selectedObjective: sampleObjective,
          settings: settings,
          focusScopes: const [],
          onSaveFocusScopes: (_) async {},
          onNext: () => nextCalled = true,
          onBack: () {},
        ),
      );

      expect(find.textContaining('Chế độ BSC BẮT BUỘC'), findsOneWidget);

      // Next button should be disabled
      final nextBtn = tester.widget<ElevatedButton>(find.byKey(const Key('btn_next_step')));
      expect(nextBtn.onPressed, isNull);

      // Now re-render with 1 scope
      final sampleScope = BscFocusScopeModel(
        id: 'scope_1',
        strategicObjectiveId: 'obj_101',
        perspective: BscPerspective.financial,
        focusDescription: 'Tăng trưởng doanh thu định kỳ ARR 120%',
        weight: 1.0,
      );

      await _pumpApp(
        tester,
        BscFocusScopeStep(
          selectedObjective: sampleObjective,
          settings: settings,
          focusScopes: [sampleScope],
          onSaveFocusScopes: (_) async {},
          onNext: () => nextCalled = true,
          onBack: () {},
        ),
      );

      final activeNextBtn = tester.widget<ElevatedButton>(find.byKey(const Key('btn_next_step')));
      expect(activeNextBtn.onPressed, isNotNull);

      await tester.tap(find.byKey(const Key('btn_next_step')));
      await tester.pumpAndSettle();
      expect(nextCalled, isTrue);
    });

    testWidgets('4. Enabled/disabled perspectives restricts perspective choices', (tester) async {
      final settings = WorkspaceStrategySettingsModel(
        workspaceId: 'ws_1',
        strategyMethod: StrategyMethod.bscFilter,
        bscMode: BscMode.required,
        enabledBscPerspectives: [
          BscPerspective.financial,
          BscPerspective.customer,
        ],
        maxTowsSelections: 2,
      );

      await _pumpApp(
        tester,
        BscFocusScopeStep(
          selectedObjective: sampleObjective,
          settings: settings,
          focusScopes: const [],
          onSaveFocusScopes: (_) async {},
          onNext: () {},
          onBack: () {},
        ),
      );

      // Open add form
      await tester.tap(find.byKey(const Key('btn_add_scope')));
      await tester.pumpAndSettle();

      // Check Dropdown options: should have Financial (Tài chính)
      expect(find.text('Tài chính'), findsWidgets);
    });

    testWidgets('5. Strategy analysis renders evidence & source provenance chips and BSC tags', (tester) async {
      final samplePestel = PestelSignalModel(
        id: 'pestel_1',
        workspaceId: 'ws_1',
        strategicObjectiveId: 'obj_101',
        dimension: PestelDimension.economic,
        statement: 'Chính sách thuế hỗ trợ doanh nghiệp phần mềm AI',
        impact: 'HIGH',
        certainty: 'HIGH',
        evidenceRefs: const ['ev_tax_decree_2026'],
        bscPerspectives: const [BscPerspective.financial],
        status: 'ACTIVE',
        revision: 1,
      );

      final sampleResource = ResourceCapabilityAssessmentModel(
        id: 'res_1',
        workspaceId: 'ws_1',
        strategicObjectiveId: 'obj_101',
        category: ResourceCapabilityCategory.financialResource,
        statement: 'Dòng tiền hoạt động ổn định trong 18 tháng',
        maturityLevel: 'HIGH',
        isStrength: true,
        evidenceRefs: const ['audit_q3_2026'],
        bscPerspectives: const [BscPerspective.financial],
        revision: 1,
      );

      final sampleSwot = SwotItemModel(
        id: 'swot_1',
        workspaceId: 'ws_1',
        strategicObjectiveId: 'obj_101',
        itemType: SwotItemType.opportunity,
        content: 'Thị trường AI SaaS doanh nghiệp mở rộng với chính sách thuế mới',
        sourcePestelSignalId: 'pestel_1',
        evidenceRefs: const ['ev_tax_decree_2026'],
        bscPerspectives: const [BscPerspective.financial],
        revision: 1,
      );

      await _pumpApp(
        tester,
        StrategyAnalysisStep(
          selectedObjective: sampleObjective,
          bscFocusScopes: const [],
          pestelSignals: [samplePestel],
          resourceAssessments: [sampleResource],
          swotItems: [sampleSwot],
          onCreatePestelSignal: ({
            required dimension,
            required statement,
            required impact,
            required certainty,
            evidenceRefs,
            bscPerspectives,
          }) async {},
          onCreateResourceAssessment: ({
            required category,
            required statement,
            required strengthLevel,
            evidenceRefs,
            bscPerspectives,
          }) async {},
          onCreateSwotItem: ({
            required itemType,
            required content,
            required sourceType,
            sourceId,
            evidenceRefs,
            bscPerspectives,
          }) async {},
          onDeriveSwotDrafts: () async {},
          onNext: () {},
          onBack: () {},
        ),
      );

      // Check selected objective context header is visible
      expect(find.textContaining('Trở thành nền tảng AI SaaS số 1 VN'), findsOneWidget);

      // Verify PESTEL tab displays the signal and evidence ref chip
      expect(find.text('Chính sách thuế hỗ trợ doanh nghiệp phần mềm AI'), findsOneWidget);
      expect(find.text('ev_tax_decree_2026'), findsOneWidget);

      // Switch to SWOT tab
      await tester.tap(find.text('Ma trận SWOT'));
      await tester.pumpAndSettle();

      // Verify SWOT displays source provenance chip
      expect(find.textContaining('Nguồn: PESTEL'), findsOneWidget);
      expect(find.text('Thị trường AI SaaS doanh nghiệp mở rộng với chính sách thuế mới'), findsOneWidget);
    });

    testWidgets('6. TOWS selection counter at 1/2 and 2/2 with policy limit enforcement', (tester) async {
      final towsOpt1 = TowsOptionModel(
        id: 'tows_1',
        workspaceId: 'ws_1',
        strategicObjectiveId: 'obj_101',
        optionType: TowsOptionType.so,
        title: 'Tăng tốc mở rộng khách hàng Enterprise ứng dụng AI',
        status: TowsOptionStatus.selected,
        impactScore: 5.0,
        difficultyScore: 3.0,
        evaluationNotes: 'Phù hợp nhất với dòng tiền hiện tại',
        revision: 1,
      );

      final towsOpt2 = TowsOptionModel(
        id: 'tows_2',
        workspaceId: 'ws_1',
        strategicObjectiveId: 'obj_101',
        optionType: TowsOptionType.so,
        title: 'Xây dựng giải pháp AI Copilot tích hợp sâu ngành',
        status: TowsOptionStatus.draft,
        impactScore: 4.0,
        difficultyScore: 4.0,
        revision: 1,
      );

      // 1. Check counter at 1 / 2
      await _pumpApp(
        tester,
        TowsPrioritizationStep(
          selectedObjective: sampleObjective,
          bscFocusScopes: const [],
          towsOptions: [towsOpt1, towsOpt2],
          selectionLimit: 2,
          onCreateOption: ({required optionType, required title, description, swotLinkIds}) async {},
          onEvaluateOption: (_, {required impactScore, required difficultyScore, rationale}) async {},
          onSelectOption: (_, {required selectionRationale}) async {},
          onRejectOption: (_, {required rejectionReason}) async {},
          onBack: () {},
        ),
      );

      expect(find.text('1 / 2 chiến lược đã chọn'), findsOneWidget);

      // 2. Check counter at 2 / 2 when both are selected
      final towsOpt2Selected = TowsOptionModel(
        id: 'tows_2',
        workspaceId: 'ws_1',
        strategicObjectiveId: 'obj_101',
        optionType: TowsOptionType.so,
        title: 'Xây dựng giải pháp AI Copilot tích hợp sâu ngành',
        status: TowsOptionStatus.selected,
        impactScore: 4.0,
        difficultyScore: 4.0,
        revision: 1,
      );

      await _pumpApp(
        tester,
        TowsPrioritizationStep(
          selectedObjective: sampleObjective,
          bscFocusScopes: const [],
          towsOptions: [towsOpt1, towsOpt2Selected],
          selectionLimit: 2,
          onCreateOption: ({required optionType, required title, description, swotLinkIds}) async {},
          onEvaluateOption: (_, {required impactScore, required difficultyScore, rationale}) async {},
          onSelectOption: (_, {required selectionRationale}) async {},
          onRejectOption: (_, {required rejectionReason}) async {},
          onBack: () {},
        ),
      );

      expect(find.text('2 / 2 chiến lược đã chọn'), findsOneWidget);
      expect(find.textContaining('Đã đạt giới hạn tối đa theo chính sách'), findsOneWidget);
    });

    testWidgets('7. No "BSC next to PESTEL" peer navigation control in StrategyLensesTab', (tester) async {
      final settings = WorkspaceStrategySettingsModel(
        workspaceId: 'ws_1',
        strategyMethod: StrategyMethod.bscFilter,
        bscMode: BscMode.optional,
        maxTowsSelections: 2,
      );

      await _pumpApp(
        tester,
        StrategyLensesTab(
          initialSettings: settings,
          initialObjectives: [sampleObjective],
          initialObjective: sampleObjective,
          initialStep: 0,
          initialFocusScopes: const [],
          initialPestelSignals: const [],
          initialResourceAssessments: const [],
          initialSwotItems: const [],
          initialTowsOptions: const [],
        ),
      );

      // Verify that old peer tabs ['PESTEL Radar', 'SWOT Bằng Chứng', 'Ma Trận TOWS', 'BSC Scorecard'] DO NOT exist
      expect(find.text('PESTEL Radar'), findsNothing);
      expect(find.text('SWOT Bằng Chứng'), findsNothing);
      expect(find.text('Ma Trận TOWS'), findsNothing);
      expect(find.text('BSC Scorecard'), findsNothing);

      // Verify step indicators exist as guided sequential flow
      expect(find.byKey(const Key('step_indicator_0')), findsOneWidget);
      expect(find.byKey(const Key('step_indicator_1')), findsOneWidget);
      expect(find.byKey(const Key('step_indicator_2')), findsOneWidget);
      expect(find.byKey(const Key('step_indicator_3')), findsOneWidget);

      // Verify dedicated read-only BSC Scorecard button exists
      expect(find.byKey(const Key('btn_view_bsc_scorecard')), findsOneWidget);
    });
  });
}
