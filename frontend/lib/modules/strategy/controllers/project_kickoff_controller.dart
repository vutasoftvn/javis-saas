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
  final roundStartDate = Rxn<DateTime>();
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
      roundStartDate.value = loaded.roundStartDate;
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

  // Mặc định vòng bắt đầu Thứ Hai kế tiếp theo lịch LOCAL của founder (khớp
  // backend nextMondayOnOrAfter: input là Thứ Hai -> trả về cùng ngày). Trả về
  // dạng UTC date-only để `.toUtc()` trong model là no-op và giữ nguyên ngày
  // lịch — nếu dùng local midnight, ở GMT+7 nó serialize lùi 1 ngày (Chủ Nhật
  // 17:00Z) và backend (`startOfUtcDay`) lưu sai ngày.
  DateTime defaultRoundStart() {
    final now = DateTime.now();
    final today = DateTime(now.year, now.month, now.day);
    final add = today.weekday == DateTime.monday ? 0 : 8 - today.weekday;
    final monday = today.add(Duration(days: add));
    return DateTime.utc(monday.year, monday.month, monday.day);
  }

  // Luôn UTC date-only: chuẩn hoá cả giá trị hydrate từ server lẫn giá trị
  // founder chọn, để `roundStartDate!.toUtc().toIso8601String()` giữ nguyên
  // ngày lịch.
  DateTime get effectiveRoundStart {
    final v = roundStartDate.value;
    if (v == null) return defaultRoundStart();
    return DateTime.utc(v.year, v.month, v.day);
  }

  void setRoundStart(DateTime d) {
    roundStartDate.value = DateTime.utc(d.year, d.month, d.day);
  }

  // Lưu ngay khi danh sách đổi — trước fix, việc #3 (hoặc bất kỳ thay đổi nào
  // ở bước 3) chỉ tồn tại trong state cục bộ tới khi bấm "Xác nhận vòng đầu";
  // nếu Founder rời màn/reload trước đó (kể cả bấm "Quay lại"), dữ liệu mất
  // vì `load()` sau đó ghi đè bằng bản trên server chưa có thay đổi này.
  Future<void> addAction(String title) async {
    // Chặn double-save khi Founder gõ nhanh 2 hành động liên tiếp trước khi
    // response đầu về — nếu không, response cũ về sau ghi đè mất action mới hơn.
    if (isSaving.value) return;
    final trimmed = title.trim();
    if (trimmed.isEmpty) return;
    if (firstWeekActions.length >= 3) return;
    firstWeekActions.add(FirstWeekActionDraft(title: trimmed));
    newActionCtrl.clear();
    await saveCurrentStep();
  }

  Future<void> removeAction(int index) async {
    if (isSaving.value) return;
    if (index < 0 || index >= firstWeekActions.length) return;
    firstWeekActions.removeAt(index);
    await saveCurrentStep();
  }

  Future<void> updateWeeklyReviewCadence({int? weekday, String? time}) async {
    if (isSaving.value) return;
    if (weekday != null) weeklyReviewWeekday.value = weekday;
    if (time != null) weeklyReviewTime.value = time;
    await saveCurrentStep();
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
      roundStartDate: roundStartDate.value,
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
      // Adopt server-assigned IDs từ response để tránh churn task ở backend.
      // Backend luôn gán id ổn định cho mỗi action; nếu id không được sync lại
      // vào firstWeekActions RxList, lần save tiếp theo sẽ gửi lên action cũ
      // mà id: null → backend sinh id MỚI → materialize churn task/commitment
      firstWeekActions.assignAll(updated.firstWeekActions);
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
