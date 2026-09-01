import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/core/contracts/enums.generated.dart';
import 'package:frontend/data/models/project_operating_setup_model.dart';
import 'package:frontend/modules/strategy/controllers/project_kickoff_controller.dart';
import 'package:frontend/modules/strategy/services/project_operating_setup_service.dart';

class FakeProjectOperatingSetupService extends ProjectOperatingSetupService {
  FakeProjectOperatingSetupService({ProjectOperatingSetup? initialSetup})
    : _setup =
          initialSetup ??
          const ProjectOperatingSetup(
            projectId: 'p-1',
            workspaceId: 'w-1',
            status: OperatingSetupStatus.notStarted,
          );

  ProjectOperatingSetup _setup;
  int saveDraftCallCount = 0;
  int activateCallCount = 0;

  @override
  Future<ProjectOperatingSetup> get(String projectId) async {
    return _setup;
  }

  @override
  Future<ProjectOperatingSetup> saveDraft(
    String projectId,
    ProjectOperatingSetupDraft draft,
  ) async {
    saveDraftCallCount++;
    _setup = ProjectOperatingSetup(
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
    return _setup;
  }

  @override
  Future<ProjectOperatingSetup> activate(
    String projectId,
    ProjectOperatingSetupDraft draft,
  ) async {
    activateCallCount++;
    _setup = ProjectOperatingSetup(
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
    return _setup;
  }
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  test('resume selects the first incomplete step', () async {
    // 1. Missing evidence -> step 0
    final c1 = ProjectKickoffController(
      service: FakeProjectOperatingSetupService(
        initialSetup: const ProjectOperatingSetup(
          projectId: 'p-1',
          workspaceId: 'w-1',
          status: OperatingSetupStatus.inProgress,
          targetCustomer: 'Founders',
          problemStatement: 'Reporting is slow',
          evidenceLevel: null,
        ),
      ),
    );
    await c1.load('p-1');
    expect(c1.currentStep.value, 0);

    // 2. Step 0 complete, step 1 incomplete -> step 1
    final c2 = ProjectKickoffController(
      service: FakeProjectOperatingSetupService(
        initialSetup: const ProjectOperatingSetup(
          projectId: 'p-1',
          workspaceId: 'w-1',
          status: OperatingSetupStatus.inProgress,
          targetCustomer: 'Founders',
          problemStatement: 'Reporting is slow',
          evidenceLevel: KickoffEvidenceLevel.oneToFourInterviews,
          selectedStage: null,
          stageDurationWeeks: null,
        ),
      ),
    );
    await c2.load('p-1');
    expect(c2.currentStep.value, 1);

    // 3. Step 0 and 1 complete -> step 2
    final c3 = ProjectKickoffController(
      service: FakeProjectOperatingSetupService(
        initialSetup: const ProjectOperatingSetup(
          projectId: 'p-1',
          workspaceId: 'w-1',
          status: OperatingSetupStatus.inProgress,
          targetCustomer: 'Founders',
          problemStatement: 'Reporting is slow',
          evidenceLevel: KickoffEvidenceLevel.oneToFourInterviews,
          selectedStage: ProjectLifecycleStage.p0Discovery,
          stageDurationWeeks: 2,
        ),
      ),
    );
    await c3.load('p-1');
    expect(c3.currentStep.value, 2);
  });

  test('selectEvidence updates stage recommendation and enforces limits', () {
    final controller = ProjectKickoffController();

    // None -> forces P0 / 2 weeks
    controller.selectEvidence(KickoffEvidenceLevel.none);
    expect(controller.selectedStage.value, ProjectLifecycleStage.p0Discovery);
    expect(controller.stageDurationWeeks.value, 2);
    expect(controller.isP1Allowed, isFalse);

    // 5+ interviews -> recommends P1 / 4 weeks
    controller.selectEvidence(KickoffEvidenceLevel.fivePlusInterviews);
    expect(
      controller.selectedStage.value,
      ProjectLifecycleStage.p1ProblemValidation,
    );
    expect(controller.stageDurationWeeks.value, 4);
    expect(controller.isP1Allowed, isTrue);
  });

  test(
    'canActivate validates all required fields and evidence requirements',
    () {
      final controller = ProjectKickoffController();
      expect(controller.canActivate, isFalse);

      controller.targetCustomerCtrl.text = 'B2B Sales';
      expect(controller.canActivate, isFalse);

      controller.problemStatementCtrl.text =
          'Lead qualification takes too long';
      expect(controller.canActivate, isFalse);

      controller.selectEvidence(KickoffEvidenceLevel.none);
      expect(controller.canActivate, isFalse);

      controller.firstWeekOutcomeCtrl.text = 'Interview 5 leads';
      expect(controller.canActivate, isFalse);

      // Add 1 action -> valid for P0
      controller.addAction('Find 10 prospects');
      expect(controller.canActivate, isTrue);

      // Try selecting P1 with NONE evidence -> canActivate is false
      controller.selectedStage.value =
          ProjectLifecycleStage.p1ProblemValidation;
      expect(controller.canActivate, isFalse);

      // Change evidence to 5+ interviews -> P1 becomes valid
      controller.selectEvidence(KickoffEvidenceLevel.fivePlusInterviews);
      controller.selectedStage.value =
          ProjectLifecycleStage.p1ProblemValidation;
      controller.stageDurationWeeks.value = 4;
      expect(controller.canActivate, isTrue);
    },
  );

  test('activate invokes service and updates setup to ACTIVE', () async {
    final fakeService = FakeProjectOperatingSetupService();
    final controller = ProjectKickoffController(service: fakeService);
    await controller.load('p-1');

    controller.targetCustomerCtrl.text = 'B2B Finance';
    controller.problemStatementCtrl.text =
        'Invoicing reconciliation is painful';
    controller.selectEvidence(KickoffEvidenceLevel.fivePlusInterviews);
    controller.selectedStage.value = ProjectLifecycleStage.p1ProblemValidation;
    controller.stageDurationWeeks.value = 4;
    controller.firstWeekOutcomeCtrl.text = 'Talk to 5 controllers';
    controller.addAction('List 10 candidate finance teams');

    expect(controller.canActivate, isTrue);
    final ok = await controller.activate();
    expect(ok, isTrue);
    expect(fakeService.activateCallCount, 1);
    expect(controller.setup.value?.status, OperatingSetupStatus.active);
  });
}
