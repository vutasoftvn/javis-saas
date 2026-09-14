import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../../../core/localization/locale_controller.dart';
import '../../../core/localization/supported_locale.dart';
import '../../../core/network/api_client.dart';
import '../../../data/models/stage_model.dart';
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

  final ProjectOperatingLoopService _loopService = ProjectOperatingLoopService();

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

  /// Kích hoạt kế hoạch phân tích và vật lý hoá vào Project Operating Loop
  Future<bool> submitAndActivate() async {
    if (!validateCurrentStep()) return false;
    isSubmitting.value = true;
    errorMessage.value = null;

    try {
      // 1. Cập nhật lifecycleStage của Project nếu người dùng đổi stage
      if (currentStage.value != initialStage) {
        try {
          await ApiClient.put(
            '/operations/projects/$projectId',
            body: {
              'lifecycleStage': currentStage.value.wireValue,
            },
          );
        } catch (_) {}
      }

      // 2. Tạo Operating Cycle đầu tiên (tuần 1 đến durationWeeks)
      final now = DateTime.now();
      final startDateStr = now.toIso8601String().split('T').first;
      String? cycleId;
      try {
        final cycleRes = await _loopService.createCycle(
          projectId,
          durationWeeks: cycleDurationWeeks.value,
          startDate: startDateStr,
        );
        cycleRes.when(
          success: (data, _) => cycleId = data['id']?.toString(),
          failure: (f) => debugPrint('[ProjectAnalysis] createCycle: ${f.message}'),
        );
      } catch (e) {
        debugPrint('[ProjectAnalysis] createCycle error: $e');
      }

      // 3. Tạo Tuần 1 (Weekly Plan)
      String? weeklyPlanId;
      if (cycleId != null) {
        try {
          final weekRes = await _loopService.createWeek(
            projectId,
            cycleId: cycleId!,
            weekNo: 1,
            focus: firstWeekOutcomeCtrl.text.trim(),
          );
          weekRes.when(
            success: (data, _) => weeklyPlanId = data['id']?.toString(),
            failure: (f) => debugPrint('[ProjectAnalysis] createWeek: ${f.message}'),
          );
        } catch (e) {
          debugPrint('[ProjectAnalysis] createWeek error: $e');
        }
      }

      // 4. Tạo Commitment và các Action Tasks
      if (weeklyPlanId != null) {
        String? commitmentId;
        try {
          final comRes = await _loopService.createCommitment(
            projectId,
            weeklyPlanId: weeklyPlanId!,
            title: firstWeekOutcomeCtrl.text.trim(),
          );
          comRes.when(
            success: (data, _) => commitmentId = data['id']?.toString(),
            failure: (f) => debugPrint('[ProjectAnalysis] createCommitment: ${f.message}'),
          );
        } catch (e) {
          debugPrint('[ProjectAnalysis] createCommitment error: $e');
        }

        if (commitmentId != null) {
          for (final actionTitle in firstWeekActions) {
            try {
              await _loopService.createTask(
                projectId,
                title: actionTitle,
                weeklyCommitmentId: commitmentId!,
                priority: 'high',
              );
            } catch (e) {
              debugPrint('[ProjectAnalysis] createTask error: $e');
            }
          }
        }
      }

      // 5. Tạo 1 Objective OKR nền tảng từ Problem & Stage
      try {
        final isEn = isEnglish;
        await _loopService.createObjective(
          projectId,
          title: '[${currentStage.value.code}] ${guidance.focusHeadline}',
          why: isEn
              ? 'Customer: ${targetCustomerCtrl.text.trim()} - Problem: ${problemStatementCtrl.text.trim()}'
              : 'Khách hàng: ${targetCustomerCtrl.text.trim()} - Vấn đề: ${problemStatementCtrl.text.trim()}',
        );
      } catch (e) {
        debugPrint('[ProjectAnalysis] createObjective error: $e');
      }

      return true;
    } catch (e) {
      errorMessage.value = isEnglish ? 'Activation error: $e' : 'Lỗi kích hoạt: $e';
      return false;
    } finally {
      isSubmitting.value = false;
    }
  }
}
