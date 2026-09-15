import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../../../core/localization/locale_controller.dart';
import '../../../core/localization/supported_locale.dart';
import '../../../core/network/api_client.dart';
import '../../../data/models/stage_model.dart';
import '../../strategy/services/okr_service.dart';
import '../models/stage_analysis_models.dart';
import '../services/project_operating_loop_service.dart';

class ProjectAnalysisFlowController extends GetxController {
  final String projectId;
  final String projectTitle;
  final ProjectStage initialStage;

  ProjectAnalysisFlowController({
    required this.projectId,
    required this.projectTitle,
    this.initialStage = ProjectStage.p0Discovery,
  });

  ProjectOperatingLoopService _loopService = ProjectOperatingLoopService();
  OkrService _okrService = OkrService();

  /// Chỉ dùng trong test để tiêm HTTP client giả — không gọi ở code sản phẩm.
  void debugOverrideService(
    ProjectOperatingLoopService loopService, {
    OkrService? okrService,
  }) {
    _loopService = loopService;
    if (okrService != null) _okrService = okrService;
  }

  bool get isEnglish {
    if (Get.isRegistered<LocaleController>()) {
      return Get.find<LocaleController>().current.value == SupportedLocale.enUS;
    }
    return Get.locale?.languageCode == 'en';
  }

  // Wizard state
  final currentStep = 0.obs;
  final isLoading = false.obs;
  final isSubmitting = false.obs;
  final isAiGenerating = false.obs;
  final errorMessage = RxnString();

  // Step 1: Customer & Problem
  final targetCustomerCtrl = TextEditingController();
  final problemStatementCtrl = TextEditingController();

  // Step 2: Stage & Evidence & Core Assumptions
  late final Rx<ProjectStage> currentStage;
  final evidenceLevel = Rx<EvidenceMaturityLevel>(EvidenceMaturityLevel.unverified);
  final selectedAssumptions = <String>[].obs;
  final customAssumptionCtrl = TextEditingController();

  // Step 3: First Week Plan (Chained from 1 & 2)
  final cycleDurationWeeks = 2.obs; // 1 to 12 weeks
  final firstWeekOutcomeCtrl = TextEditingController();
  final firstWeekActions = <String>[].obs;
  final newActionCtrl = TextEditingController();

  StageGuidanceTemplate get guidance =>
      StageAnalysisKnowledge.getTemplate(currentStage.value, isEnglish ? 'en' : 'vi');

  @override
  void onInit() {
    super.onInit();
    currentStage = Rx<ProjectStage>(initialStage);
    _applyGuidanceDefaults();
  }

  @override
  void onClose() {
    targetCustomerCtrl.dispose();
    problemStatementCtrl.dispose();
    customAssumptionCtrl.dispose();
    firstWeekOutcomeCtrl.dispose();
    newActionCtrl.dispose();
    super.onClose();
  }

  void _applyGuidanceDefaults() {
    final tpl = guidance;
    if (selectedAssumptions.isEmpty) {
      selectedAssumptions.assignAll(tpl.coreAssumptions);
    }
  }

  void onStageChanged(ProjectStage newStage) {
    currentStage.value = newStage;
    final tpl = StageAnalysisKnowledge.getTemplate(newStage, isEnglish ? 'en' : 'vi');
    selectedAssumptions.assignAll(tpl.coreAssumptions);
    
    // Tự động điều chỉnh tuần theo stage
    if (newStage == ProjectStage.p0Discovery) {
      cycleDurationWeeks.value = 2;
    } else if (newStage == ProjectStage.p1ProblemValidation) {
      cycleDurationWeeks.value = 4;
    } else {
      cycleDurationWeeks.value = 6;
    }
  }

  void toggleAssumption(String item) {
    if (selectedAssumptions.contains(item)) {
      selectedAssumptions.remove(item);
    } else {
      selectedAssumptions.add(item);
    }
  }

  void addCustomAssumption() {
    final text = customAssumptionCtrl.text.trim();
    if (text.isNotEmpty && !selectedAssumptions.contains(text)) {
      selectedAssumptions.add(text);
      customAssumptionCtrl.clear();
    }
  }

  void addFirstWeekAction([String? actionText]) {
    final text = (actionText ?? newActionCtrl.text).trim();
    if (text.isNotEmpty && !firstWeekActions.contains(text)) {
      firstWeekActions.add(text);
      if (actionText == null) newActionCtrl.clear();
    }
  }

  void removeFirstWeekAction(int index) {
    if (index >= 0 && index < firstWeekActions.length) {
      firstWeekActions.removeAt(index);
    }
  }

  /// AI sinh Outcome và Actions dựa trên ngữ cảnh đã nhập ở Bước 1 & Bước 2
  Future<void> generateAiSuggestions() async {
    isAiGenerating.value = true;
    try {
      final isEn = isEnglish;
      final customer = targetCustomerCtrl.text.trim();
      final problem = problemStatementCtrl.text.trim();
      final stageName = isEn ? currentStage.value.displayNameEn : currentStage.value.displayNameVi;
      final stageCode = currentStage.value.code;
      final assumptionsCount = selectedAssumptions.length;

      // Thử gọi AI qua route chat nếu có, hoặc tạo template tổng hợp ngữ cảnh chính xác
      final suggestedOutcome = customer.isNotEmpty && problem.isNotEmpty
          ? (isEn
              ? '[$stageCode - $stageName] Validate solution for "$customer" addressing problem "$problem" ($assumptionsCount core assumptions).'
              : '[$stageCode - $stageName] Xác thực giải pháp cho "$customer" đối với vấn đề "$problem" ($assumptionsCount giả định cốt lõi).')
          : guidance.suggestedOutcomeTemplate;

      firstWeekOutcomeCtrl.text = suggestedOutcome;

      // Sinh 2-3 action hành động cụ thể gắn liền với context
      firstWeekActions.clear();
      if (customer.isNotEmpty) {
        firstWeekActions.add(
          isEn
              ? 'Build target list of 10 matching customers: $customer'
              : 'Lập danh sách 10 khách hàng mục tiêu phù hợp: $customer',
        );
      }
      for (final act in guidance.suggestedFirstWeekActions) {
        if (!firstWeekActions.contains(act)) {
          firstWeekActions.add(act);
        }
      }
    } finally {
      isAiGenerating.value = false;
    }
  }

  bool validateCurrentStep() {
    errorMessage.value = null;
    final isEn = isEnglish;
    if (currentStep.value == 0) {
      if (targetCustomerCtrl.text.trim().isEmpty) {
        errorMessage.value = isEn
            ? 'Please enter your target customer / ICP.'
            : 'Vui lòng nhập đối tượng khách hàng mục tiêu.';
        return false;
      }
      if (problemStatementCtrl.text.trim().isEmpty) {
        errorMessage.value = isEn
            ? 'Please describe the core problem or pain point your project solves.'
            : 'Vui lòng mô tả vấn đề/nỗi đau cốt lõi mà dự án giải quyết.';
        return false;
      }
    } else if (currentStep.value == 1) {
      if (selectedAssumptions.isEmpty) {
        errorMessage.value = isEn
            ? 'Please select or add at least 1 core assumption to validate.'
            : 'Vui lòng chọn hoặc thêm ít nhất 1 giả định cốt lõi cần kiểm chứng.';
        return false;
      }
    } else if (currentStep.value == 2) {
      if (firstWeekOutcomeCtrl.text.trim().isEmpty) {
        errorMessage.value = isEn
            ? 'Please enter the key outcome for the first week.'
            : 'Vui lòng nhập kết quả then chốt (Outcome) của tuần đầu tiên.';
        return false;
      }
      if (firstWeekActions.isEmpty) {
        errorMessage.value = isEn
            ? 'Please add at least 1 priority action for the first week.'
            : 'Vui lòng thêm ít nhất 1 hành động ưu tiên cho tuần đầu tiên.';
        return false;
      }
    }
    return true;
  }

  void nextStep() {
    if (!validateCurrentStep()) return;
    if (currentStep.value < 2) {
      currentStep.value++;
      if (currentStep.value == 2 && firstWeekOutcomeCtrl.text.isEmpty) {
        generateAiSuggestions();
      }
    }
  }

  void prevStep() {
    errorMessage.value = null;
    if (currentStep.value > 0) {
      currentStep.value--;
    }
  }

  /// Kích hoạt kế hoạch phân tích và vật lý hoá vào Project Operating Loop.
  ///
  /// Thứ tự bắt buộc: Objective → Key Result(s) → Publish → Cycle (gắn
  /// `sourceObjectiveId` ngay lúc tạo) → Week → Commitment → Task. Cycle phải
  /// được tạo SAU khi Objective đã publish, nếu không cycle sẽ vĩnh viễn
  /// không gắn được với objective nào (bug gốc: cycle tạo trước, objective
  /// tạo sau, không có field nào nối 2 bên).
  Future<bool> submitAndActivate() async {
    if (!validateCurrentStep()) return false;
    isSubmitting.value = true;
    errorMessage.value = null;
    final isEn = isEnglish;
    final warnings = <String>[];

    try {
      // 1. Cập nhật lifecycleStage của Project nếu người dùng đổi stage.
      if (currentStage.value != initialStage) {
        try {
          await ApiClient.put(
            '/operations/projects/$projectId',
            body: {'lifecycleStage': currentStage.value.wireValue},
          );
        } catch (e) {
          warnings.add('lifecycleStage: $e');
        }
      }

      // 2. Tạo Objective OKR nền tảng từ Problem & Stage.
      String? objectiveId;
      final objRes = await _loopService.createObjective(
        projectId,
        title: '[${currentStage.value.code}] ${guidance.focusHeadline}',
        why: isEn
            ? 'Customer: ${targetCustomerCtrl.text.trim()} - Problem: ${problemStatementCtrl.text.trim()}'
            : 'Khách hàng: ${targetCustomerCtrl.text.trim()} - Vấn đề: ${problemStatementCtrl.text.trim()}',
      );
      objRes.when(
        success: (data, _) => objectiveId = data['id']?.toString(),
        failure: (f) => warnings.add('createObjective: ${f.message}'),
      );

      if (objectiveId == null) {
        errorMessage.value = isEn
            ? 'Could not create the strategic objective. Please try again.'
            : 'Không thể tạo mục tiêu chiến lược (Objective). Vui lòng thử lại.';
        return false;
      }

      // 3. Tạo 1..3 Key Result từ giả định cốt lõi đã chọn — publishObjective
      // (bước 4) bắt buộc objective phải có 1..3 Key Result hợp lệ mới cho
      // publish (okr.service.ts: requireStrategyGovernanceAuthority + KR
      // validation).
      var keyResultCount = 0;
      for (final assumption in selectedAssumptions.take(3)) {
        final krRes = await _loopService.createKeyResult(
          projectId,
          objectiveId: objectiveId!,
          title: assumption,
          targetValue: 1,
          unit: isEn ? 'validated' : 'đã kiểm chứng',
          baselineValue: 0,
          currentValue: 0,
        );
        krRes.when(
          success: (_, _) => keyResultCount++,
          failure: (f) => warnings.add('createKeyResult: ${f.message}'),
        );
      }

      if (keyResultCount == 0) {
        errorMessage.value = isEn
            ? 'Could not create any key result for the objective. Please try again.'
            : 'Không thể tạo Key Result nào cho mục tiêu. Vui lòng thử lại.';
        return false;
      }

      // 4. Publish Objective — nếu bỏ qua bước này, Cycle ở bước 5 sẽ liên
      // kết tới 1 objective mãi ở trạng thái draft.
      try {
        await _okrService.publishObjective(objectiveId!);
      } catch (e) {
        errorMessage.value = isEn
            ? 'Could not publish the objective: $e'
            : 'Không thể công bố (publish) mục tiêu: $e';
        return false;
      }

      // 5. Tạo Operating Cycle, gắn thẳng sourceObjectiveId ngay lúc tạo.
      final now = DateTime.now();
      final startDateStr = now.toIso8601String().split('T').first;
      String? cycleId;
      final cycleRes = await _loopService.createCycle(
        projectId,
        durationWeeks: cycleDurationWeeks.value,
        startDate: startDateStr,
        sourceObjectiveId: objectiveId,
      );
      cycleRes.when(
        success: (data, _) => cycleId = data['id']?.toString(),
        failure: (f) => warnings.add('createCycle: ${f.message}'),
      );

      if (cycleId == null) {
        errorMessage.value = isEn
            ? 'Could not create the operating cycle. Please try again.'
            : 'Không thể tạo chu kỳ hoạt động (Operating Cycle). Vui lòng thử lại.';
        return false;
      }

      // 6. Tạo Tuần 1 (Weekly Plan).
      String? weeklyPlanId;
      final weekRes = await _loopService.createWeek(
        projectId,
        cycleId: cycleId!,
        weekNo: 1,
        focus: firstWeekOutcomeCtrl.text.trim(),
      );
      weekRes.when(
        success: (data, _) => weeklyPlanId = data['id']?.toString(),
        failure: (f) => warnings.add('createWeek: ${f.message}'),
      );

      // 7. Tạo Commitment và các Action Task — không chặn submit nếu lỗi ở
      // đây, nhưng phải báo cho founder biết thay vì debugPrint âm thầm.
      if (weeklyPlanId != null) {
        String? commitmentId;
        final comRes = await _loopService.createCommitment(
          projectId,
          weeklyPlanId: weeklyPlanId!,
          title: firstWeekOutcomeCtrl.text.trim(),
        );
        comRes.when(
          success: (data, _) => commitmentId = data['id']?.toString(),
          failure: (f) => warnings.add('createCommitment: ${f.message}'),
        );

        if (commitmentId != null) {
          for (final actionTitle in firstWeekActions) {
            final taskRes = await _loopService.createTask(
              projectId,
              title: actionTitle,
              weeklyCommitmentId: commitmentId!,
              priority: 'high',
            );
            taskRes.when(
              success: (_, _) {},
              failure: (f) => warnings.add('createTask($actionTitle): ${f.message}'),
            );
          }
        } else {
          warnings.add('createCommitment did not return an id, skipping tasks');
        }
      }

      if (warnings.isNotEmpty) {
        errorMessage.value = isEn
            ? 'Plan activated with warnings: ${warnings.join('; ')}'
            : 'Kế hoạch đã kích hoạt nhưng có cảnh báo: ${warnings.join('; ')}';
      }

      return true;
    } catch (e) {
      errorMessage.value = isEn ? 'Activation error: $e' : 'Lỗi kích hoạt: $e';
      return false;
    } finally {
      isSubmitting.value = false;
    }
  }
}
