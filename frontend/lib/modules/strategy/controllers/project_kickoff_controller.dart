import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../../../core/contracts/enums.generated.dart';
import '../../../data/models/project_operating_setup_model.dart';
import '../services/project_operating_setup_service.dart';

class ProjectKickoffController extends GetxController {
  final ProjectOperatingSetupService _service;

  ProjectKickoffController({ProjectOperatingSetupService? service})
    : _service = service ?? ProjectOperatingSetupService();

  final projectId = ''.obs;
  final setup = Rxn<ProjectOperatingSetup>();
  final currentStep = 0.obs;
  final isLoading = false.obs;
  final isSaving = false.obs;
  final isActivating = false.obs;
  final errorMessage = RxnString();

  final targetCustomerCtrl = TextEditingController();
  final problemStatementCtrl = TextEditingController();
  final evidenceLevel = Rxn<KickoffEvidenceLevel>();
  final selectedStage = Rx<ProjectLifecycleStage>(
    ProjectLifecycleStage.p0Discovery,
  );
  final stageDurationWeeks = 2.obs;
  final weeklyReviewWeekday = 5.obs;
  final weeklyReviewTime = '16:00'.obs;
  final firstWeekOutcomeCtrl = TextEditingController();
  final firstWeekActions = <FirstWeekActionDraft>[].obs;
  final newActionCtrl = TextEditingController();

  @override
  void onClose() {
    targetCustomerCtrl.dispose();
    problemStatementCtrl.dispose();
    firstWeekOutcomeCtrl.dispose();
    newActionCtrl.dispose();
    super.onClose();
  }

  Future<void> load(String id) async {
    projectId.value = id;
    isLoading.value = true;
    errorMessage.value = null;
    try {
      final loaded = await _service.get(id);
      setup.value = loaded;

      targetCustomerCtrl.text = loaded.targetCustomer ?? '';
      problemStatementCtrl.text = loaded.problemStatement ?? '';
      evidenceLevel.value = loaded.evidenceLevel;

      final stage =
          loaded.selectedStage ??
          (loaded.evidenceLevel != null
              ? KickoffStagePolicy.recommend(loaded.evidenceLevel)
              : ProjectLifecycleStage.p0Discovery);
      selectedStage.value = stage;

      stageDurationWeeks.value =
          loaded.stageDurationWeeks ??
          (stage == ProjectLifecycleStage.p1ProblemValidation ? 4 : 2);

      weeklyReviewWeekday.value = loaded.weeklyReviewWeekday ?? 5;
      weeklyReviewTime.value = loaded.weeklyReviewTime ?? '16:00';
      firstWeekOutcomeCtrl.text = loaded.firstWeekOutcome ?? '';

      firstWeekActions.assignAll(loaded.firstWeekActions);

      // Determine initial / resumed step
      if (loaded.targetCustomer == null ||
          loaded.targetCustomer!.trim().isEmpty ||
          loaded.problemStatement == null ||
          loaded.problemStatement!.trim().isEmpty ||
          loaded.evidenceLevel == null) {
        currentStep.value = 0;
      } else if (loaded.selectedStage == null ||
          loaded.stageDurationWeeks == null) {
        currentStep.value = 1;
      } else {
        currentStep.value = 2;
      }
    } catch (e) {
      errorMessage.value = e.toString();
    } finally {
      isLoading.value = false;
    }
  }

  void selectEvidence(KickoffEvidenceLevel level) {
    evidenceLevel.value = level;
    final recommended = KickoffStagePolicy.recommend(level);
    if (level == KickoffEvidenceLevel.none ||
        level == KickoffEvidenceLevel.oneToFourInterviews) {
      selectedStage.value = ProjectLifecycleStage.p0Discovery;
      stageDurationWeeks.value = 2;
    } else {
      selectedStage.value = recommended;
      stageDurationWeeks.value = 4;
    }
  }

  void selectStage(ProjectLifecycleStage stage) {
    if (stage == ProjectLifecycleStage.p1ProblemValidation) {
      if (evidenceLevel.value != KickoffEvidenceLevel.fivePlusInterviews &&
          evidenceLevel.value != KickoffEvidenceLevel.prototypeOrRevenue) {
        return;
      }
      selectedStage.value = stage;
      stageDurationWeeks.value = 4;
    } else {
      selectedStage.value = ProjectLifecycleStage.p0Discovery;
      stageDurationWeeks.value = 2;
    }
  }

  void selectDuration(int weeks) {
    if (KickoffStagePolicy.allows(selectedStage.value, weeks)) {
      stageDurationWeeks.value = weeks;
    }
  }

  void addAction(String title) {
    final trimmed = title.trim();
    if (trimmed.isEmpty) return;
    if (firstWeekActions.length >= 3) return;
    firstWeekActions.add(FirstWeekActionDraft(title: trimmed));
    newActionCtrl.clear();
  }

  void removeAction(int index) {
    if (index >= 0 && index < firstWeekActions.length) {
      firstWeekActions.removeAt(index);
    }
  }

  bool get isP1Allowed =>
      evidenceLevel.value == KickoffEvidenceLevel.fivePlusInterviews ||
      evidenceLevel.value == KickoffEvidenceLevel.prototypeOrRevenue;

  bool get canActivate {
    if (targetCustomerCtrl.text.trim().isEmpty) return false;
    if (problemStatementCtrl.text.trim().isEmpty) return false;
    if (evidenceLevel.value == null) return false;
    if (selectedStage.value == ProjectLifecycleStage.p1ProblemValidation &&
        !isP1Allowed) {
      return false;
    }
    if (!KickoffStagePolicy.allows(
      selectedStage.value,
      stageDurationWeeks.value,
    )) {
      return false;
    }
    if (firstWeekOutcomeCtrl.text.trim().isEmpty) return false;
    if (firstWeekActions.isEmpty || firstWeekActions.length > 3) return false;
    if (firstWeekActions.any((a) => a.title.trim().isEmpty)) return false;
    return true;
  }

  ProjectOperatingSetupDraft buildDraft() {
    return ProjectOperatingSetupDraft(
      targetCustomer: targetCustomerCtrl.text.trim().isNotEmpty
          ? targetCustomerCtrl.text.trim()
          : null,
      problemStatement: problemStatementCtrl.text.trim().isNotEmpty
          ? problemStatementCtrl.text.trim()
          : null,
      evidenceLevel: evidenceLevel.value,
      selectedStage: selectedStage.value,
      stageDurationWeeks: stageDurationWeeks.value,
      weeklyReviewWeekday: weeklyReviewWeekday.value,
      weeklyReviewTime: weeklyReviewTime.value,
      firstWeekOutcome: firstWeekOutcomeCtrl.text.trim().isNotEmpty
          ? firstWeekOutcomeCtrl.text.trim()
          : null,
      firstWeekActions: firstWeekActions.toList(),
    );
  }

  Future<bool> saveCurrentStep() async {
    if (projectId.value.isEmpty) return false;
    isSaving.value = true;
    errorMessage.value = null;
    try {
      final updated = await _service.saveDraft(projectId.value, buildDraft());
      setup.value = updated;
      return true;
    } catch (e) {
      errorMessage.value = e.toString();
      return false;
    } finally {
      isSaving.value = false;
    }
  }

  Future<bool> activate() async {
    if (!canActivate || projectId.value.isEmpty) return false;
    isActivating.value = true;
    errorMessage.value = null;
    try {
      final activated = await _service.activate(projectId.value, buildDraft());
      setup.value = activated;
      return true;
    } catch (e) {
      errorMessage.value = e.toString();
      return false;
    } finally {
      isActivating.value = false;
    }
  }
}
