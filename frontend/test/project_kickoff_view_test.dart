import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:get/get.dart';
import 'package:frontend/core/contracts/enums.generated.dart';
import 'package:frontend/data/models/project_operating_setup_model.dart';
import 'package:frontend/modules/strategy/controllers/project_kickoff_controller.dart';
import 'package:frontend/modules/strategy/services/project_operating_setup_service.dart';
import 'package:frontend/modules/strategy/views/project_kickoff_view.dart';
import 'package:frontend/modules/strategy/views/project_stage_workspace_view.dart';
import 'package:frontend/modules/strategy/controllers/project_orchestration_controller.dart';

class FakeKickoffService extends ProjectOperatingSetupService {
  FakeKickoffService({this.initialSetup});
  final ProjectOperatingSetup? initialSetup;

  @override
  Future<ProjectOperatingSetup> get(String projectId) async {
    return initialSetup ??
        ProjectOperatingSetup(
          projectId: projectId,
          workspaceId: 'w-1',
          status: OperatingSetupStatus.notStarted,
        );
  }

  @override
  Future<ProjectOperatingSetup> saveDraft(
    String projectId,
    ProjectOperatingSetupDraft draft,
  ) async {
    return ProjectOperatingSetup(
      projectId: projectId,
      workspaceId: 'w-1',
      status: OperatingSetupStatus.inProgress,
      targetCustomer: draft.targetCustomer,
      problemStatement: draft.problemStatement,
      evidenceLevel: draft.evidenceLevel,
      selectedStage: draft.selectedStage,
      stageDurationWeeks: draft.stageDurationWeeks,
      weeklyReviewWeekday: draft.weeklyReviewWeekday,
      weeklyReviewTime: draft.weeklyReviewTime,
      firstWeekOutcome: draft.firstWeekOutcome,
      firstWeekActions: draft.firstWeekActions,
    );
  }

  @override
  Future<ProjectOperatingSetup> activate(
    String projectId,
    ProjectOperatingSetupDraft draft,
  ) async {
    return ProjectOperatingSetup(
      projectId: projectId,
      workspaceId: 'w-1',
      status: OperatingSetupStatus.active,
      targetCustomer: draft.targetCustomer,
      problemStatement: draft.problemStatement,
      evidenceLevel: draft.evidenceLevel,
      selectedStage: draft.selectedStage,
      stageDurationWeeks: draft.stageDurationWeeks,
      weeklyReviewWeekday: draft.weeklyReviewWeekday,
      weeklyReviewTime: draft.weeklyReviewTime,
      firstWeekOutcome: draft.firstWeekOutcome,
      firstWeekActions: draft.firstWeekActions,
    );
  }
}

Widget kickoffHarness({
  required ProjectOperatingSetup setup,
  void Function(String id)? onActivated,
  VoidCallback? onBack,
  VoidCallback? onOpenAdvancedRoadmap,
}) {
  Get.reset();
  Get.put(
    ProjectKickoffController(service: FakeKickoffService(initialSetup: setup)),
    tag: setup.projectId,
  );

  return GetMaterialApp(
    home: Scaffold(
      body: ProjectKickoffView(
        projectId: setup.projectId,
        onBack: onBack ?? () {},
        onActivated: onActivated ?? (_) {},
        onOpenAdvancedRoadmap: onOpenAdvancedRoadmap ?? () {},
      ),
    ),
  );
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() {
    Get.reset();
    Get.testMode = true;
  });

  final draftP0Setup = const ProjectOperatingSetup(
    projectId: 'p-1',
    workspaceId: 'w-1',
    status: OperatingSetupStatus.inProgress,
    targetCustomer: 'Fintech CFOs',
    problemStatement: 'Manual reconciliation takes 3 days',
    evidenceLevel: KickoffEvidenceLevel.none,
  );

  final completeP0Draft = const ProjectOperatingSetup(
    projectId: 'p-1',
    workspaceId: 'w-1',
    status: OperatingSetupStatus.inProgress,
    targetCustomer: 'Fintech CFOs',
    problemStatement: 'Manual reconciliation takes 3 days',
    evidenceLevel: KickoffEvidenceLevel.none,
    selectedStage: ProjectLifecycleStage.p0Discovery,
    stageDurationWeeks: 2,
    weeklyReviewWeekday: 5,
    weeklyReviewTime: '16:00',
    firstWeekOutcome: 'Talk to 5 CFOs',
    firstWeekActions: [FirstWeekActionDraft(title: 'List 10 target CFOs')],
  );

  testWidgets(
    'disposing kickoff view for one project does not break a still-mounted '
    'view for a different project (regression: shared untagged controller '
    'used to dispose TextEditingControllers out from under a sibling view)',
    (tester) async {
      Get.reset();
      Get.put(
        ProjectKickoffController(
          service: FakeKickoffService(initialSetup: draftP0Setup),
        ),
        tag: 'p-1',
      );
      final draftP0SetupOtherProject = const ProjectOperatingSetup(
        projectId: 'p-2',
        workspaceId: 'w-1',
        status: OperatingSetupStatus.inProgress,
        targetCustomer: 'Fintech CFOs',
        problemStatement: 'Manual reconciliation takes 3 days',
        evidenceLevel: KickoffEvidenceLevel.none,
      );
      Get.put(
        ProjectKickoffController(
          service: FakeKickoffService(initialSetup: draftP0SetupOtherProject),
        ),
        tag: 'p-2',
      );

      final showFirst = ValueNotifier<bool>(true);

      await tester.pumpWidget(
        GetMaterialApp(
          home: Scaffold(
            body: ValueListenableBuilder<bool>(
              valueListenable: showFirst,
              builder: (context, show, _) {
                return Column(
                  children: [
                    if (show)
                      Expanded(
                        child: ProjectKickoffView(
                          projectId: 'p-1',
                          onBack: () {},
                          onActivated: (_) {},
                          onOpenAdvancedRoadmap: () {},
                        ),
                      ),
                    Expanded(
                      child: ProjectKickoffView(
                        projectId: 'p-2',
                        onBack: () {},
                        onActivated: (_) {},
                        onOpenAdvancedRoadmap: () {},
                      ),
                    ),
                  ],
                );
              },
            ),
          ),
        ),
      );
      await tester.pumpAndSettle();

      // Simulate the `p-1` view being popped off the Navigator stack (its
      // dispose() deletes its own tagged controller) while `p-2`'s view
      // stays mounted and keeps rendering.
      showFirst.value = false;
      await tester.pumpAndSettle();

      expect(tester.takeException(), isNull);
      expect(
        find.text('COSA đề xuất: Khám phá (P0) trong 2 tuần'),
        findsOneWidget,
      );
    },
  );

  testWidgets('P0 proposes two weeks and does not show 12-Week Year', (
    tester,
  ) async {
    await tester.pumpWidget(kickoffHarness(setup: draftP0Setup));
    await tester.pumpAndSettle();

    expect(
      find.text('COSA đề xuất: Khám phá (P0) trong 2 tuần'),
      findsOneWidget,
    );
    expect(find.textContaining('12-Week Year'), findsNothing);
    expect(find.textContaining('12 tuần'), findsNothing);
  });

  testWidgets(
    'selecting an evidence radio updates the UI reactively '
    '(regression: content wrapped in LayoutBuilder escaped Obx tracking so '
    'radios/steps stopped rebuilding)',
    (tester) async {
      final draftNoEvidence = const ProjectOperatingSetup(
        projectId: 'p-1',
        workspaceId: 'w-1',
        status: OperatingSetupStatus.inProgress,
        targetCustomer: 'Fintech CFOs',
        problemStatement: 'Manual reconciliation takes 3 days',
        // evidenceLevel null -> resume ở bước 0, nút "Tiếp tục" bị disable.
      );
      await tester.pumpWidget(kickoffHarness(setup: draftNoEvidence));
      await tester.pumpAndSettle();

      ElevatedButton continueBtn() => tester.widget<ElevatedButton>(
        find.widgetWithText(ElevatedButton, 'Tiếp tục'),
      );
      expect(continueBtn().onPressed, isNull);

      final radioFinder = find.text('Có từ 5 cuộc trao đổi');
      await tester.ensureVisible(radioFinder);
      await tester.pumpAndSettle();
      await tester.tap(radioFinder);
      await tester.pumpAndSettle();

      // Nếu Obx không rebuild, nút vẫn disable -> test fail.
      expect(continueBtn().onPressed, isNotNull);
    },
  );

  testWidgets('tapping a completed step tab navigates back to that step', (
    tester,
  ) async {
    await tester.pumpWidget(kickoffHarness(setup: completeP0Draft));
    await tester.pumpAndSettle();

    // completeP0Draft resume ở bước 3.
    expect(find.text('Bước 3: Chốt việc tuần đầu'), findsOneWidget);

    await tester.tap(find.text('Hiểu dự án'));
    await tester.pumpAndSettle();

    expect(find.text('Bước 1: Hiểu dự án'), findsOneWidget);
  });

  testWidgets('activate navigates only after success', (tester) async {
    final activated = <String>[];
    await tester.pumpWidget(
      kickoffHarness(
        setup: completeP0Draft,
        onActivated: (id) => activated.add(id),
      ),
    );
    await tester.pumpAndSettle();

    final buttonFinder = find.widgetWithText(
      ElevatedButton,
      'Xác nhận vòng đầu',
    );
    expect(buttonFinder, findsOneWidget);
    await tester.ensureVisible(buttonFinder);
    await tester.tap(buttonFinder);
    await tester.pumpAndSettle();

    expect(activated, ['p-1']);
  });

  testWidgets('activation disabled when target customer is empty', (
    tester,
  ) async {
    final controller = ProjectKickoffController();
    controller.targetCustomerCtrl.text = '';
    controller.problemStatementCtrl.text = 'Reconciliation is painful';
    controller.selectEvidence(KickoffEvidenceLevel.none);
    controller.firstWeekOutcomeCtrl.text = 'Talk to 5 CFOs';
    controller.addAction('List 10 prospects');
    expect(controller.canActivate, isFalse);
  });

  testWidgets('activation disabled when problem statement is empty', (
    tester,
  ) async {
    final controller = ProjectKickoffController();
    controller.targetCustomerCtrl.text = 'CFOs';
    controller.problemStatementCtrl.text = '';
    controller.selectEvidence(KickoffEvidenceLevel.none);
    controller.firstWeekOutcomeCtrl.text = 'Talk to 5 CFOs';
    controller.addAction('List 10 prospects');
    expect(controller.canActivate, isFalse);
  });

  testWidgets('activation disabled when first-week outcome is empty', (
    tester,
  ) async {
    final controller = ProjectKickoffController();
    controller.targetCustomerCtrl.text = 'CFOs';
    controller.problemStatementCtrl.text = 'Reconciliation is painful';
    controller.selectEvidence(KickoffEvidenceLevel.none);
    controller.firstWeekOutcomeCtrl.text = '';
    controller.addAction('List 10 prospects');
    expect(controller.canActivate, isFalse);
  });

  testWidgets('activation disabled when action list has zero entries', (
    tester,
  ) async {
    final controller = ProjectKickoffController();
    controller.targetCustomerCtrl.text = 'CFOs';
    controller.problemStatementCtrl.text = 'Reconciliation is painful';
    controller.selectEvidence(KickoffEvidenceLevel.none);
    controller.firstWeekOutcomeCtrl.text = 'Talk to 5 CFOs';
    expect(controller.canActivate, isFalse);
  });

  testWidgets(
    'P1 selected with NONE evidence is disallowed and shows explanation',
    (tester) async {
      final controller = ProjectKickoffController();
      controller.targetCustomerCtrl.text = 'CFOs';
      controller.problemStatementCtrl.text = 'Reconciliation is painful';
      controller.selectEvidence(KickoffEvidenceLevel.none);
      controller.selectedStage.value =
          ProjectLifecycleStage.p1ProblemValidation;
      controller.firstWeekOutcomeCtrl.text = 'Talk to 5 CFOs';
      controller.addAction('List 10 prospects');

      expect(controller.canActivate, isFalse);
      expect(controller.isP1Allowed, isFalse);
    },
  );

  testWidgets(
    'legal/regulated review requirement is visible before activation',
    (WidgetTester tester) async {
      final controller = Get.put(ProjectOrchestrationController());
      controller.serviceAssessments.assignAll([
        {
          'id': 'a1',
          'disposition': 'REQUIRED',
          'reason': 'Regulated compliance checklist needed',
          'risk_level': 'REGULATED',
          'execution_mode': 'MANUAL',
          'professional_review_required': true,
          'status': 'DRAFT',
        },
        {
          'id': 'a2',
          'disposition': 'OPTIONAL',
          'reason': 'Nice-to-have GTM support',
          'risk_level': 'LOW',
          'execution_mode': 'AI_ASSISTED',
          'professional_review_required': false,
          'status': 'DRAFT',
        },
      ]);

      await tester.pumpWidget(
        GetMaterialApp(
          home: Scaffold(
            body: ProjectStageWorkspaceView(
              projectId: '100',
              stageId: 's1',
              onBack: () {},
            ),
          ),
        ),
      );

      expect(find.text('Cần chuyên gia phê duyệt'), findsOneWidget);
    },
  );
}
