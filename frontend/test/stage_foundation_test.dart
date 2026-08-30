import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/data/models/stage_model.dart';
import 'package:frontend/shared/widgets/stage_badge.dart';
import 'package:frontend/modules/hologram_hub/widgets/stage_selector_header.dart';

void main() {
  group('COSA Stage Foundation Models Test', () {
    test('uses canonical project-stage values', () {
      expect(ProjectStage.p0Discovery.wireValue, 'P0_DISCOVERY');
      expect(ProjectStage.p1ProblemValidation.wireValue, 'P1_PROBLEM_VALIDATION');
      expect(ProjectStage.p2SolutionValidation.wireValue, 'P2_SOLUTION_VALIDATION');
      expect(ProjectStage.p3BuildValidate.wireValue, 'P3_BUILD_VALIDATE');
      expect(ProjectStage.p4GoToMarket.wireValue, 'P4_GO_TO_MARKET');
      expect(ProjectStage.p5OperateGrowth.wireValue, 'P5_OPERATE_GROWTH');
      expect(ProjectStage.p6ScaleGovern.wireValue, 'P6_SCALE_GOVERN');

      expect(ProjectStage.tryFromWire('S1_PROBLEM_VALIDATION'), isNull);
      expect(ProjectStage.tryFromWire('P0_DISCOVERY'), ProjectStage.p0Discovery);
      expect(ProjectStage.tryFromWire('P3_BUILD_VALIDATE'), ProjectStage.p3BuildValidate);

      expect(ProjectStage.p0Discovery.code, 'P0');
      expect(ProjectStage.p1ProblemValidation.code, 'P1');
      expect(ProjectStage.p5OperateGrowth.code, 'P5');
      expect(ProjectStage.p1ProblemValidation.toServerString(), 'P1_PROBLEM_VALIDATION');
    });

    test('StageContextModel deserialization from JSON', () {
      final json = {
        'workspace_id': 1001,
        'company_stage': 'P5_OPERATE_GROWTH',
        'company_vision': 'Empower Founders',
        'company_mission': 'Automate Ops',
        'company_values': ['Focus', 'Evidence'],
        'project_id': 2001,
        'project_title': 'AI Hotel Intelligence',
        'project_type': 'NEW_BUSINESS',
        'project_stage': 'P2_SOLUTION_VALIDATION',
        'stage_goal': 'Validate willingness to pay',
        'critical_constraints': ['High setup time'],
        'exit_criteria': {'paid_pilots': 2},
        'stage_metadata': {},
        'policy': {
          'stage': 'P2_SOLUTION_VALIDATION',
          'stage_name_vi': 'Xác Thực Giải Pháp',
          'code': 'P2',
          'primary_goal': 'Xác thực giá trị giải pháp',
          'primary_questions': ['Khách hàng có trả tiền không?'],
          'required_entities': ['prototype_spec', 'pricing_hypothesis'],
          'primary_metrics': ['activation_rate', 'paid_pilot_count'],
          'deemphasized_tools': ['bsc', 'nps'],
          'recommended_methods': ['lean_experiment', 'pricing_test'],
          'optional_lenses': ['pestel'],
          'priority_agents': ['Product Agent'],
          'review_cadence': 'weekly',
        },
      };

      final model = StageContextModel.fromJson(json);

      expect(model.workspaceId, 1001);
      expect(model.companyStage, 'P5_OPERATE_GROWTH');
      expect(model.projectId, 2001);
      expect(model.projectTitle, 'AI Hotel Intelligence');
      expect(model.projectStage, ProjectStage.p2SolutionValidation);
      expect(model.policy.code, 'P2');
      expect(model.policy.recommendedMethods, contains('lean_experiment'));
      expect(model.criticalConstraints, contains('High setup time'));
    });
  });

  group('COSA Stage Foundation Widgets Test', () {
    testWidgets('StageBadge renders correctly with icon and code', (WidgetTester tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: Center(
              child: StageBadge(
                stage: ProjectStage.p1ProblemValidation,
                showFullName: true,
              ),
            ),
          ),
        ),
      );

      expect(find.text('P1'), findsOneWidget);
      expect(find.textContaining('Xác thực nỗi đau'), findsOneWidget);
      expect(find.byIcon(Icons.psychology_outlined), findsOneWidget);
    });

    testWidgets('StageSelectorHeader renders with StageBadge and project title', (WidgetTester tester) async {
      final policy = StagePolicyModel(
        stage: ProjectStage.p4GoToMarket,
        stageNameVi: 'Đưa Ra Thị Trường',
        code: 'P4',
        primaryGoal: 'Tìm kiếm kênh lặp lại',
        primaryQuestions: ['Kênh nào tối ưu?'],
        requiredEntities: ['sales_funnel'],
        primaryMetrics: ['cac', 'mrr'],
        deemphasizedTools: ['bsc'],
        recommendedMethods: ['sales_playbook'],
        optionalLenses: ['tows'],
        priorityAgents: ['Marketing Agent'],
        reviewCadence: 'weekly',
      );

      final contextModel = StageContextModel(
        workspaceId: 1001,
        companyStage: 'P5_OPERATE_GROWTH',
        companyValues: [],
        projectId: 5001,
        projectTitle: 'Marketing Hub SaaS',
        projectStage: ProjectStage.p4GoToMarket,
        stageGoal: 'Tìm 1 kênh thu hút khách hàng ổn định',
        criticalConstraints: ['CAC cao'],
        exitCriteria: {},
        stageMetadata: {},
        policy: policy,
      );

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: StageSelectorHeader(
              contextModel: contextModel,
              onProjectChanged: (_) {},
            ),
          ),
        ),
      );

      expect(find.text('Marketing Hub SaaS'), findsOneWidget);
      expect(find.text('P4'), findsOneWidget);
      expect(find.textContaining('Tìm 1 kênh thu hút khách hàng ổn định', findRichText: true), findsOneWidget);
      expect(find.byIcon(Icons.info_outline), findsOneWidget);
    });
  });
}
