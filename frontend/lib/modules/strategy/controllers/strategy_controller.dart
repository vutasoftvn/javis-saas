import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../../../core/theme/app_theme.dart';
import '../../../data/services/strategy_service.dart';

class StrategyController extends GetxController {
  final StrategyService _strategyService = StrategyService();

  final isLoading = false.obs;
  final isSaving = false.obs;
  final isGeneratingAi = false.obs;
  final errorMessage = RxnString();

  // OKRs & Cycles
  final okrCycles = <dynamic>[].obs;
  final selectedCycleId = RxnString();
  final objectives = <dynamic>[].obs;
  final keyResults = <dynamic>[].obs;
  final expandedObjectiveId = RxnString();

  // 12-Week Execution
  final twelveWeekCycles = <dynamic>[].obs;
  final weeklyPlans = <dynamic>[].obs;
  final weeklyCommitments = <dynamic>[].obs;
  final selectedPlanId = RxnString();

  // Strategic Analysis (PESTEL, SWOT, TOWS)
  final pestelItems = <dynamic>[].obs;
  final swotItems = <dynamic>[].obs;
  final towsOptions = <dynamic>[].obs;

  // Projects & Initiatives
  final projects = <dynamic>[].obs;
  final initiatives = <dynamic>[].obs;

  // mCOSA V12 Stage-Gate & Governance
  final cycleStages = <dynamic>[].obs;
  final milestones = <dynamic>[].obs;
  final gateDecisions = <dynamic>[].obs;
  final cycleContract = Rxn<Map<String, dynamic>>();
  final cycleCompilationStatus = Rxn<Map<String, dynamic>>();

  // mCOSA V12 Weekly Review & Week 13 Strategic Transition
  final weeklyReviews = <dynamic>[].obs;
  final currentWeek13Review = Rxn<Map<String, dynamic>>();
  final currentCelebration = Rxn<Map<String, dynamic>>();
  final week13Readiness = Rxn<Map<String, dynamic>>();

  // mCOSA V12 Portfolio Intelligence (Sprint 6)
  final portfolios = <dynamic>[].obs;
  final portfolioDetection = Rxn<Map<String, dynamic>>();
  final selectedPortfolioId = Rxn<String>();
  final currentPortfolioProjects = <dynamic>[].obs;
  final currentPortfolioPestel = <dynamic>[].obs;
  final currentImpactMatrix = Rxn<Map<String, dynamic>>();

  // mCOSA V12 Sprint 7 Portfolio SWOT, TOWS, Options & Synergies
  final currentPortfolioSwot = <dynamic>[].obs;
  final currentPortfolioTows = <dynamic>[].obs;
  final currentPortfolioSynergies = <dynamic>[].obs;
  final currentPortfolioDependencies = <dynamic>[].obs;
  final currentPortfolioOptions = <dynamic>[].obs;

  // mCOSA V12 Sprint 8 Portfolio Cycles & Founder Profile (WIP Limit)
  final founderProfile = Rxn<Map<String, dynamic>>();
  final currentPortfolioCycles = <dynamic>[].obs;

  // mCOSA V12 Sprint 9 Next Best Action Engine
  final ceoNextActions = <dynamic>[].obs;

  // mCOSA V12 Sprint 10 Living PESTEL & Model Profiles
  final pestelSignals = <dynamic>[].obs;
  final modelRunsAudit = <dynamic>[].obs;
  final modelProfiles = <dynamic>[].obs;

  @override
  void onInit() {
    super.onInit();
    loadAllData();
    loadFounderProfile();
    loadCeoNextActions();
  }



  Future<void> _runGuarded(Future<void> Function() action, {bool showSnackbar = false}) async {
    errorMessage.value = null;
    try {
      await action();
    } on StrategyApiException catch (e) {
      errorMessage.value = e.message;
      if (showSnackbar) {
        Get.snackbar(
          'Thông báo',
          e.message,
          snackPosition: SnackPosition.BOTTOM,
          backgroundColor: const Color(0xFFE11D48),
          colorText: Colors.white,
          margin: const EdgeInsets.all(16),
          borderRadius: 12,
        );
      }
    } catch (e) {
      errorMessage.value = 'Lỗi: $e';
    }
  }

  Future<void> loadAllData() async {
    isLoading.value = true;
    await Future.wait([
      loadOkrs(),
      loadExecution(),
      loadAnalysis(),
      loadProjects(),
    ]);
    isLoading.value = false;
  }

  // ====================================================================
  // OKRs
  // ====================================================================

  Future<void> loadOkrs() async {
    await _runGuarded(() async {
      final cycles = await _strategyService.getOkrCycles();
      okrCycles.value = cycles;
      if (cycles.isNotEmpty && selectedCycleId.value == null) {
        selectedCycleId.value = cycles.first['id'];
      }

      final objs = await _strategyService.getObjectives(cycleId: selectedCycleId.value);
      objectives.value = objs;

      final krs = await _strategyService.getKeyResults();
      keyResults.value = krs;
    });
  }

  List<dynamic> getKeyResultsForObjective(String objectiveId) {
    return keyResults.where((kr) => kr['objective_id'] == objectiveId).toList();
  }

  double calculateObjectiveProgress(String objectiveId) {
    final krs = getKeyResultsForObjective(objectiveId);
    if (krs.isEmpty) return 0.0;
    double totalProgress = 0.0;
    for (final kr in krs) {
      final baseline = (kr['baseline_value'] as num?)?.toDouble() ?? 0.0;
      final target = (kr['target_value'] as num?)?.toDouble() ?? 100.0;
      final current = (kr['current_value'] as num?)?.toDouble() ?? 0.0;
      if (target > baseline) {
        final ratio = (current - baseline) / (target - baseline);
        totalProgress += ratio.clamp(0.0, 1.0);
      } else {
        totalProgress += 1.0;
      }
    }
    return (totalProgress / krs.length).clamp(0.0, 1.0);
  }

  Future<void> createOkrCycle(String name, {DateTime? startDate, DateTime? endDate}) async {
    isSaving.value = true;
    await _runGuarded(() async {
      final cycle = await _strategyService.createOkrCycle(name: name, startDate: startDate, endDate: endDate);
      await loadOkrs();
      selectedCycleId.value = cycle['id'];
      Get.snackbar('Thành công', 'Đã tạo chu kỳ OKR mới', snackPosition: SnackPosition.BOTTOM, backgroundColor: const Color(0xFF10B981), colorText: Colors.white);
    }, showSnackbar: true);
    isSaving.value = false;
  }

  Future<void> createObjective(String title, {String? status}) async {
    isSaving.value = true;
    await _runGuarded(() async {
      await _strategyService.createObjective(title: title, cycleId: selectedCycleId.value, status: status);
      await loadOkrs();
      Get.snackbar('Thành công', 'Đã thêm mục tiêu OKR', snackPosition: SnackPosition.BOTTOM, backgroundColor: const Color(0xFF10B981), colorText: Colors.white);
    }, showSnackbar: true);
    isSaving.value = false;
  }

  void toggleObjectiveExpanded(String objectiveId) {
    if (expandedObjectiveId.value == objectiveId) {
      expandedObjectiveId.value = null;
    } else {
      expandedObjectiveId.value = objectiveId;
    }
  }

  Future<void> updateObjective(String objectiveId, {String? title, String? status}) async {
    isSaving.value = true;
    await _runGuarded(() async {
      await _strategyService.updateObjective(objectiveId, title: title, status: status);
      await loadOkrs();
    }, showSnackbar: true);
    isSaving.value = false;
  }

  Future<void> deleteObjective(String objectiveId) async {
    isSaving.value = true;
    await _runGuarded(() async {
      await _strategyService.deleteObjective(objectiveId);
      await loadOkrs();
      Get.snackbar('Thành công', 'Đã xóa mục tiêu OKR', snackPosition: SnackPosition.BOTTOM, backgroundColor: const Color(0xFF10B981), colorText: Colors.white);
    }, showSnackbar: true);
    isSaving.value = false;
  }

  Future<void> createKeyResult({
    required String objectiveId,
    String? title,
    required double baselineValue,
    required double targetValue,
    required double currentValue,
    required String unit,
    String? cadence,
  }) async {
    isSaving.value = true;
    await _runGuarded(() async {
      await _strategyService.createKeyResult(
        objectiveId: objectiveId,
        title: title,
        baselineValue: baselineValue,
        targetValue: targetValue,
        currentValue: currentValue,
        unit: unit,
        cadence: cadence,
      );
      await loadOkrs();
      Get.snackbar('Thành công', 'Đã thêm Kết quả Then chốt (Key Result)', snackPosition: SnackPosition.BOTTOM, backgroundColor: const Color(0xFF10B981), colorText: Colors.white);
    }, showSnackbar: true);
    isSaving.value = false;
  }

  Future<void> updateKeyResult(String keyResultId, {double? currentValue, double? targetValue, String? status}) async {
    isSaving.value = true;
    await _runGuarded(() async {
      await _strategyService.updateKeyResult(keyResultId, currentValue: currentValue, targetValue: targetValue, status: status);
      await loadOkrs();
      Get.snackbar('Thành công', 'Đã cập nhật tiến độ Key Result', snackPosition: SnackPosition.BOTTOM, backgroundColor: const Color(0xFF10B981), colorText: Colors.white);
    }, showSnackbar: true);
    isSaving.value = false;
  }

  Future<void> deleteKeyResult(String keyResultId) async {
    isSaving.value = true;
    await _runGuarded(() async {
      await _strategyService.deleteKeyResult(keyResultId);
      await loadOkrs();
      Get.snackbar('Thành công', 'Đã xóa Key Result', snackPosition: SnackPosition.BOTTOM, backgroundColor: const Color(0xFF10B981), colorText: Colors.white);
    }, showSnackbar: true);
    isSaving.value = false;
  }

  // ====================================================================
  // 12-Week Execution
  // ====================================================================

  Future<void> loadExecution() async {
    await _runGuarded(() async {
      final cycles = await _strategyService.getTwelveWeekCycles();
      twelveWeekCycles.value = cycles;

      final plans = await _strategyService.getWeeklyPlans();
      weeklyPlans.value = plans;

      final commitments = await _strategyService.getWeeklyCommitments();
      weeklyCommitments.value = commitments;
    });
  }

  List<dynamic> getCommitmentsForPlan(String planId) {
    return weeklyCommitments.where((c) => c['weekly_plan_id'] == planId).toList();
  }

  Future<void> createWeeklyPlan(int weekNo, {String? focus, DateTime? startDate}) async {
    isSaving.value = true;
    await _runGuarded(() async {
      await _strategyService.createWeeklyPlan(weekNo: weekNo, focus: focus, startDate: startDate);
      await loadExecution();
      Get.snackbar('Thành công', 'Đã tạo kế hoạch tuần $weekNo', snackPosition: SnackPosition.BOTTOM, backgroundColor: const Color(0xFF10B981), colorText: Colors.white);
    }, showSnackbar: true);
    isSaving.value = false;
  }

  Future<void> createWeeklyCommitment(String planId, String title, {String? effort}) async {
    isSaving.value = true;
    await _runGuarded(() async {
      await _strategyService.createWeeklyCommitment(weeklyPlanId: planId, title: title, plannedEffort: effort);
      await loadExecution();
      Get.snackbar('Thành công', 'Đã thêm cam kết công việc', snackPosition: SnackPosition.BOTTOM, backgroundColor: const Color(0xFF10B981), colorText: Colors.white);
    }, showSnackbar: true);
    isSaving.value = false;
  }

  Future<void> toggleCommitmentStatus(String commitmentId, String currentStatus) async {
    final newStatus = currentStatus == 'done' ? 'todo' : 'done';
    isSaving.value = true;
    await _runGuarded(() async {
      await _strategyService.updateWeeklyCommitment(commitmentId, status: newStatus);
      await loadExecution();
    }, showSnackbar: true);
    isSaving.value = false;
  }

  Future<void> deleteWeeklyCommitment(String commitmentId) async {
    isSaving.value = true;
    await _runGuarded(() async {
      await _strategyService.deleteWeeklyCommitment(commitmentId);
      await loadExecution();
    }, showSnackbar: true);
    isSaving.value = false;
  }

  // ====================================================================
  // Strategic Analysis (PESTEL, SWOT, TOWS)
  // ====================================================================

  final foundationVision = ''.obs;
  final foundationMission = ''.obs;
  final foundationCoreValues = <dynamic>[].obs;

  Future<void> loadAnalysis() async {
    await _runGuarded(() async {
      pestelItems.value = await _strategyService.getPestelItems();
      swotItems.value = await _strategyService.getSwotItems();
      towsOptions.value = await _strategyService.getTowsOptions();
      await loadFoundationContext();
    });
  }

  Future<void> loadFoundationContext() async {
    try {
      final canvases = await _strategyService.getCanvases();
      if (canvases.isNotEmpty) {
        final canvasId = canvases.first['id'];
        final canvasDetail = await _strategyService.getCanvasDetail(canvasId);
        final revisions = canvasDetail['revisions'] as List<dynamic>?;
        if (revisions != null && revisions.isNotEmpty) {
          final latestRev = revisions.first;
          final revDetail = await _strategyService.getRevisionDetail(latestRev['id']);
          final found = revDetail['foundation'];
          if (found != null) {
            foundationVision.value = found['vision'] ?? '';
            foundationMission.value = found['mission'] ?? '';
            foundationCoreValues.value = (found['values'] as List<dynamic>?) ?? [];
          }
        }
      }
    } catch (_) {}
  }

  Future<void> createPestelItem({required String factor, required String statement, String? impact}) async {
    isSaving.value = true;
    await _runGuarded(() async {
      await _strategyService.createPestelItem(factor: factor, statement: statement, impact: impact);
      await loadAnalysis();
      Get.snackbar('Thành công', 'Đã thêm mục phân tích PESTEL', snackPosition: SnackPosition.BOTTOM, backgroundColor: const Color(0xFF10B981), colorText: Colors.white);
    }, showSnackbar: true);
    isSaving.value = false;
  }

  Future<void> updatePestelItem(String id, {required String factor, required String statement, String? impact}) async {
    isSaving.value = true;
    await _runGuarded(() async {
      await _strategyService.updatePestelItem(id, factor: factor, statement: statement, impact: impact);
      await loadAnalysis();
      Get.snackbar('Thành công', 'Đã cập nhật mục phân tích PESTEL', snackPosition: SnackPosition.BOTTOM, backgroundColor: const Color(0xFF10B981), colorText: Colors.white);
    }, showSnackbar: true);
    isSaving.value = false;
  }

  Future<void> deletePestelItem(String id) async {
    isSaving.value = true;
    await _runGuarded(() async {
      await _strategyService.deletePestelItem(id);
      await loadAnalysis();
    }, showSnackbar: true);
    isSaving.value = false;
  }

  Future<void> createSwotItem({required String category, required String statement, String? impact}) async {
    isSaving.value = true;
    await _runGuarded(() async {
      await _strategyService.createSwotItem(category: category, statement: statement, impact: impact);
      await loadAnalysis();
      Get.snackbar('Thành công', 'Đã thêm mục phân tích SWOT', snackPosition: SnackPosition.BOTTOM, backgroundColor: const Color(0xFF10B981), colorText: Colors.white);
    }, showSnackbar: true);
    isSaving.value = false;
  }

  Future<void> updateSwotItem(String id, {required String category, required String statement, String? impact}) async {
    isSaving.value = true;
    await _runGuarded(() async {
      await _strategyService.updateSwotItem(id, category: category, statement: statement, impact: impact);
      await loadAnalysis();
      Get.snackbar('Thành công', 'Đã cập nhật mục phân tích SWOT', snackPosition: SnackPosition.BOTTOM, backgroundColor: const Color(0xFF10B981), colorText: Colors.white);
    }, showSnackbar: true);
    isSaving.value = false;
  }

  Future<void> deleteSwotItem(String id) async {
    isSaving.value = true;
    await _runGuarded(() async {
      await _strategyService.deleteSwotItem(id);
      await loadAnalysis();
    }, showSnackbar: true);
    isSaving.value = false;
  }

  Future<void> createTowsOption({required String quadrant, required String title, required String tradeoffs}) async {
    isSaving.value = true;
    await _runGuarded(() async {
      await _strategyService.createTowsOption(quadrant: quadrant, title: title, tradeoffs: tradeoffs);
      await loadAnalysis();
      Get.snackbar('Thành công', 'Đã thêm lựa chọn chiến lược TOWS', snackPosition: SnackPosition.BOTTOM, backgroundColor: const Color(0xFF10B981), colorText: Colors.white);
    }, showSnackbar: true);
    isSaving.value = false;
  }

  Future<void> updateTowsOption(String id, {required String quadrant, required String title, required String tradeoffs}) async {
    isSaving.value = true;
    await _runGuarded(() async {
      await _strategyService.updateTowsOption(id, quadrant: quadrant, title: title, tradeoffs: tradeoffs);
      await loadAnalysis();
      Get.snackbar('Thành công', 'Đã cập nhật lựa chọn chiến lược TOWS', snackPosition: SnackPosition.BOTTOM, backgroundColor: const Color(0xFF10B981), colorText: Colors.white);
    }, showSnackbar: true);
    isSaving.value = false;
  }

  Future<void> deleteTowsOption(String id) async {
    isSaving.value = true;
    await _runGuarded(() async {
      await _strategyService.deleteTowsOption(id);
      await loadAnalysis();
    }, showSnackbar: true);
    isSaving.value = false;
  }

  Future<void> generateAiAnalysis({
    String? projectId,
    String? focusArea,
    bool clearExisting = true,
    int? pestelItemsPerFactor,
    int? swotItemsPerCategory,
    int? towsItemsPerQuadrant,
  }) async {
    isGeneratingAi.value = true;
    await _runGuarded(() async {
      await _strategyService.generateAiAnalysis(
        projectId: projectId,
        focusArea: focusArea,
        clearExisting: clearExisting,
        pestelItemsPerFactor: pestelItemsPerFactor,
        swotItemsPerCategory: swotItemsPerCategory,
        towsItemsPerQuadrant: towsItemsPerQuadrant,
      );
      await loadAnalysis();
      Get.snackbar(
        'Hoàn thành',
        'AI đã hoàn thành phân tích chuyên sâu (PESTEL, SWOT & TOWS)',
        snackPosition: SnackPosition.BOTTOM,
        backgroundColor: AppTheme.surfaceDarkElevated,
        colorText: Colors.white,
      );
    }, showSnackbar: true);
    isGeneratingAi.value = false;
  }

  Future<void> generateAiOkrs({
    String? towsId,
    int objectivesCount = 2,
    int krsPerObjectiveCount = 3,
    String? cycleId,
  }) async {
    isGeneratingAi.value = true;
    await _runGuarded(() async {
      await _strategyService.generateAiOkrs(
        towsId: towsId,
        objectivesCount: objectivesCount,
        krsPerObjectiveCount: krsPerObjectiveCount,
        cycleId: cycleId,
      );
      await loadOkrs();
      Get.snackbar(
        'Hoàn thành',
        'AI đã tạo tự động $objectivesCount Mục tiêu cùng $krsPerObjectiveCount Kết quả Then chốt/mục tiêu',
        snackPosition: SnackPosition.BOTTOM,
        backgroundColor: AppTheme.surfaceDarkElevated,
        colorText: Colors.white,
      );
    }, showSnackbar: true);
    isGeneratingAi.value = false;
  }

  Future<Map<String, dynamic>> getPromptTemplate() async {
    return await _strategyService.getPromptTemplate();
  }

  Future<void> updatePromptTemplate({
    String? templateContent,
    int? pestelItemsPerFactor,
    int? swotItemsPerCategory,
    int? towsItemsPerQuadrant,
  }) async {
    isSaving.value = true;
    await _runGuarded(() async {
      await _strategyService.updatePromptTemplate(
        templateContent: templateContent,
        pestelItemsPerFactor: pestelItemsPerFactor,
        swotItemsPerCategory: swotItemsPerCategory,
        towsItemsPerQuadrant: towsItemsPerQuadrant,
      );
      Get.snackbar(
        'Thành công',
        'Đã lưu và đồng bộ Prompt mẫu cho Workspace',
        snackPosition: SnackPosition.BOTTOM,
        backgroundColor: AppTheme.success,
        colorText: Colors.white,
      );
    }, showSnackbar: true);
    isSaving.value = false;
  }

  Future<void> resetPromptTemplate() async {
    isSaving.value = true;
    await _runGuarded(() async {
      await _strategyService.resetPromptTemplate();
      Get.snackbar(
        'Đã khôi phục',
        'Đã khôi phục Prompt mẫu về mặc định hệ thống',
        snackPosition: SnackPosition.BOTTOM,
        backgroundColor: AppTheme.surfaceDarkElevated,
        colorText: Colors.white,
      );
    }, showSnackbar: true);
    isSaving.value = false;
  }

  // ====================================================================
  // Strategic Projects & Initiatives
  // ====================================================================

  Future<void> loadProjects() async {
    await _runGuarded(() async {
      projects.value = await _strategyService.getProjects();
      initiatives.value = await _strategyService.getInitiatives();
      await loadPortfolios();
      await detectPortfolioNecessity();
    });
  }


  Future<void> createProject({
    required String title,
    String? phase,
    String? currentGate,
    String? status,
  }) async {
    isSaving.value = true;
    await _runGuarded(() async {
      await _strategyService.createProject(title: title, phase: phase, currentGate: currentGate, status: status);
      await loadProjects();
      Get.snackbar('Thành công', 'Đã tạo dự án chiến lược mới', snackPosition: SnackPosition.BOTTOM, backgroundColor: const Color(0xFF10B981), colorText: Colors.white);
    }, showSnackbar: true);
    isSaving.value = false;
  }

  Future<void> updateProject(
    String projectId, {
    String? title,
    String? phase,
    String? currentGate,
    String? status,
  }) async {
    isSaving.value = true;
    await _runGuarded(() async {
      await _strategyService.updateProject(projectId, title: title, phase: phase, currentGate: currentGate, status: status);
      await loadProjects();
      Get.snackbar('Thành công', 'Đã cập nhật dự án', snackPosition: SnackPosition.BOTTOM, backgroundColor: const Color(0xFF10B981), colorText: Colors.white);
    }, showSnackbar: true);
    isSaving.value = false;
  }

  Future<void> deleteProject(String projectId) async {
    isSaving.value = true;
    await _runGuarded(() async {
      await _strategyService.deleteProject(projectId);
      await loadProjects();
      Get.snackbar('Thành công', 'Đã xóa dự án', snackPosition: SnackPosition.BOTTOM, backgroundColor: const Color(0xFF10B981), colorText: Colors.white);
    }, showSnackbar: true);
    isSaving.value = false;
  }

  Future<void> createInitiative({required String title, String? projectId, String? status}) async {
    isSaving.value = true;
    await _runGuarded(() async {
      await _strategyService.createInitiative(title: title, projectId: projectId, status: status);
      await loadProjects();
      Get.snackbar('Thành công', 'Đã thêm sáng kiến', snackPosition: SnackPosition.BOTTOM, backgroundColor: const Color(0xFF10B981), colorText: Colors.white);
    }, showSnackbar: true);
    isSaving.value = false;
  }

  // ====================================================================
  // mCOSA V12 Single Project Journey & Assisted Terra
  // ====================================================================

  Future<Map<String, dynamic>?> classifyProject(
    String projectId, {
    String? titleOverride,
    String? descriptionOverride,
  }) async {
    isGeneratingAi.value = true;
    Map<String, dynamic>? result;
    await _runGuarded(() async {
      result = await _strategyService.classifyProject(
        projectId,
        titleOverride: titleOverride,
        descriptionOverride: descriptionOverride,
      );
      await loadProjects();
      Get.snackbar(
        'Phân loại hoàn tất',
        'Dự án đã được phân loại: ${result?['project_type'] ?? ''}',
        snackPosition: SnackPosition.BOTTOM,
        backgroundColor: const Color(0xFF10B981),
        colorText: Colors.white,
      );
    }, showSnackbar: true);
    isGeneratingAi.value = false;
    return result;
  }

  Future<Map<String, dynamic>?> routeMethodology(
    String projectId, {
    List<String>? customMethodologies,
    String? rationaleOverride,
  }) async {
    isSaving.value = true;
    Map<String, dynamic>? result;
    await _runGuarded(() async {
      result = await _strategyService.routeMethodology(
        projectId,
        customMethodologies: customMethodologies,
        rationaleOverride: rationaleOverride,
      );
      await loadProjects();
      Get.snackbar(
        'Thành công',
        'Đã cập nhật lộ trình phương pháp',
        snackPosition: SnackPosition.BOTTOM,
        backgroundColor: const Color(0xFF10B981),
        colorText: Colors.white,
      );
    }, showSnackbar: true);
    isSaving.value = false;
    return result;
  }

  Future<Map<String, dynamic>?> exportAnalysisPrompt({
    String? projectId,
    String? canvasId,
  }) async {
    Map<String, dynamic>? result;
    await _runGuarded(() async {
      result = await _strategyService.exportAnalysisPrompt(
        projectId: projectId,
        canvasId: canvasId,
      );
    }, showSnackbar: true);
    return result;
  }

  Future<Map<String, dynamic>?> importAnalysisResult(
    String rawInput, {
    String? projectId,
    String? canvasId,
  }) async {
    isSaving.value = true;
    Map<String, dynamic>? result;
    await _runGuarded(() async {
      result = await _strategyService.importAnalysisResult(
        rawInput,
        projectId: projectId,
        canvasId: canvasId,
      );
      await loadAllData();
      Get.snackbar(
        'Nhập thành công',
        'Đã tạo bản sửa đổi chiến lược mới từ kết quả Terra (${result?['pestel_count'] ?? 0} PESTEL, ${result?['swot_count'] ?? 0} SWOT, ${result?['tows_count'] ?? 0} TOWS)',
        snackPosition: SnackPosition.BOTTOM,
        backgroundColor: const Color(0xFF10B981),
        colorText: Colors.white,
      );
    }, showSnackbar: true);
    isSaving.value = false;
    return result;
  }

  // ====================================================================
  // mCOSA V12 Stage-Gate Governance & Weekly Mission (Sprint 3)
  // ====================================================================

  Future<void> loadCycleGovernance(String cycleId) async {
    await _runGuarded(() async {
      cycleStages.value = await _strategyService.getCycleStages(cycleId);
      milestones.value = await _strategyService.getMilestones(cycleId: cycleId);
      cycleContract.value = await _strategyService.getCycleContract(cycleId);
      gateDecisions.value = await _strategyService.getGateDecisions();
    });
  }

  Future<void> generateStandardStages(String cycleId) async {
    isSaving.value = true;
    await _runGuarded(() async {
      cycleStages.value = await _strategyService.generateStandardCycleStages(cycleId);
      Get.snackbar(
        'Thành công',
        'Đã tạo 5 giai đoạn chuẩn (13-Week Stages) cho chu kỳ',
        snackPosition: SnackPosition.BOTTOM,
        backgroundColor: const Color(0xFF10B981),
        colorText: Colors.white,
      );
    }, showSnackbar: true);
    isSaving.value = false;
  }

  Future<void> createMilestone({
    required String name,
    String? cycleId,
    String? stageId,
    String? projectId,
    String? description,
    int? dueWeek,
    String? acceptanceCriteria,
  }) async {
    isSaving.value = true;
    await _runGuarded(() async {
      await _strategyService.createMilestone(
        name: name,
        cycleId: cycleId,
        stageId: stageId,
        projectId: projectId,
        description: description,
        dueWeek: dueWeek,
        acceptanceCriteria: acceptanceCriteria,

      );
      if (cycleId != null) await loadCycleGovernance(cycleId);
      Get.snackbar('Thành công', 'Đã thêm Milestone mới', snackPosition: SnackPosition.BOTTOM, backgroundColor: const Color(0xFF10B981), colorText: Colors.white);
    }, showSnackbar: true);
    isSaving.value = false;
  }

  Future<void> recordGateDecision({
    required String projectId,
    required String decision,
    required String rationale,
    String? milestoneId,
    String? stageId,
    String? evidenceSummary,
    String? nextStepInstructions,
    String? cycleId,
  }) async {
    isSaving.value = true;
    await _runGuarded(() async {
      await _strategyService.recordGateDecision(
        projectId: projectId,
        decision: decision,
        rationale: rationale,
        milestoneId: milestoneId,
        stageId: stageId,
        evidenceSummary: evidenceSummary,
        nextStepInstructions: nextStepInstructions,
      );
      if (cycleId != null) await loadCycleGovernance(cycleId);
      await loadProjects();
      Get.snackbar(
        'Quyết định Cổng đã lưu',
        'Cổng kiểm soát ghi nhận quyết định: $decision',
        snackPosition: SnackPosition.BOTTOM,
        backgroundColor: const Color(0xFF10B981),
        colorText: Colors.white,
      );
    }, showSnackbar: true);
    isSaving.value = false;
  }

  Future<void> upsertCycleContract(
    String cycleId, {
    required String successDefinition,
    double? founderCapacityPerWeek,
    double? reservedBufferPercent,
    double? aiBudget,
    double? operatingBudget,
    String? status,
  }) async {
    isSaving.value = true;
    await _runGuarded(() async {
      final res = await _strategyService.upsertCycleContract(
        cycleId,
        successDefinition: successDefinition,
        founderCapacityPerWeek: founderCapacityPerWeek,
        reservedBufferPercent: reservedBufferPercent,
        aiBudget: aiBudget,
        operatingBudget: operatingBudget,
        status: status,
      );
      cycleContract.value = res;
      Get.snackbar(
        'Thành công',
        'Đã ký kết hợp đồng chu kỳ 12 tuần',
        snackPosition: SnackPosition.BOTTOM,
        backgroundColor: const Color(0xFF10B981),
        colorText: Colors.white,
      );
    }, showSnackbar: true);
    isSaving.value = false;
  }

  Future<void> updateWeeklyMission(
    String planId, {
    String? mission,
    Map<String, dynamic>? successCriteria,
    String? stageId,
    double? outcomeScore,
  }) async {
    isSaving.value = true;
    await _runGuarded(() async {
      await _strategyService.updateWeeklyMission(
        planId,
        mission: mission,
        successCriteria: successCriteria,
        stageId: stageId,
        outcomeScore: outcomeScore,
      );
      await loadExecution();
      Get.snackbar(
        'Thành công',
        'Đã cập nhật Weekly Mission & Tiêu chí thành công',
        snackPosition: SnackPosition.BOTTOM,
        backgroundColor: const Color(0xFF10B981),
        colorText: Colors.white,
      );
    }, showSnackbar: true);
    isSaving.value = false;
  }

  // ====================================================================
  // mCOSA V12 Planning Compiler to V10 Runtime (Sprint 4)
  // ====================================================================

  Future<void> loadCycleCompilationStatus(String cycleId) async {
    await _runGuarded(() async {
      cycleCompilationStatus.value = await _strategyService.getCycleCompilationStatus(cycleId);
    });
  }

  Future<void> compileCycle(String cycleId) async {
    isSaving.value = true;
    await _runGuarded(() async {
      final res = await _strategyService.compileCycle(cycleId);
      await loadCycleCompilationStatus(cycleId);
      await loadExecution();
      Get.snackbar(
        'Biên dịch thành công',
        'Đã tạo ${res['tasks_created']} tác vụ (Tasks) và ${res['outcomes_created']} mục tiêu kết quả (Outcomes) cho runtime V10',
        snackPosition: SnackPosition.BOTTOM,
        backgroundColor: const Color(0xFF10B981),
        colorText: Colors.white,
      );
    }, showSnackbar: true);
    isSaving.value = false;
  }

  Future<void> compileWeeklyPlan(String planId) async {
    isSaving.value = true;
    await _runGuarded(() async {
      final res = await _strategyService.compileWeeklyPlan(planId);
      await loadExecution();
      Get.snackbar(
        'Biên dịch Tuần thành công',
        'Đã tạo ${res['tasks_created']} tác vụ (Tasks) cho tuần ${res['week_no']}',
        snackPosition: SnackPosition.BOTTOM,
        backgroundColor: const Color(0xFF10B981),
        colorText: Colors.white,
      );
    }, showSnackbar: true);
    isSaving.value = false;
  }

  // ====================================================================
  // mCOSA V12 Weekly Review & Week 13 Transition (Sprint 5)
  // ====================================================================

  Future<void> loadWeeklyReviews(String cycleId) async {
    await _runGuarded(() async {
      weeklyReviews.value = await _strategyService.getWeeklyReviews(cycleId);
    });
  }

  Future<void> createWeeklyReview(
    String cycleId, {
    required String weeklyPlanId,
    required double executionScore,
    required double outcomeScore,
    String? evidenceLearned,
    Map<String, dynamic>? assumptionsConfirmed,
    Map<String, dynamic>? assumptionsInvalidated,
    String? recommendation,
    String? narrativeSummary,
  }) async {
    isSaving.value = true;
    await _runGuarded(() async {
      await _strategyService.createWeeklyReview(
        cycleId,
        weeklyPlanId: weeklyPlanId,
        executionScore: executionScore,
        outcomeScore: outcomeScore,
        evidenceLearned: evidenceLearned,
        assumptionsConfirmed: assumptionsConfirmed,
        assumptionsInvalidated: assumptionsInvalidated,
        recommendation: recommendation,
        narrativeSummary: narrativeSummary,
      );
      await loadWeeklyReviews(cycleId);
      await loadExecution();
      Get.snackbar(
        'Lưu Đánh Giá Tuần Thành Công',
        'Đã lưu điểm số, bằng chứng và khuyến nghị: $recommendation',
        snackPosition: SnackPosition.BOTTOM,
        backgroundColor: const Color(0xFF10B981),
        colorText: Colors.white,
      );
    }, showSnackbar: true);
    isSaving.value = false;
  }

  Future<void> loadWeek13Readiness(String cycleId) async {
    await _runGuarded(() async {
      week13Readiness.value = await _strategyService.getWeek13Readiness(cycleId);
      currentWeek13Review.value = await _strategyService.getWeek13Review(cycleId);
      currentCelebration.value = await _strategyService.getWeek13Celebration(cycleId);
    });
  }

  Future<void> finalizeWeek13(
    String cycleId, {
    required double overallExecutionScore,
    required double overallOutcomeScore,
    required double okrAchievementRate,
    String? strategicLearnings,
    String? systemicBlockers,
    Map<String, dynamic>? portfolioAdjustments,
    String? nextCycleRecommendations,
    String? celebrationTitle,
    Map<String, dynamic>? milestonesAchieved,
    Map<String, dynamic>? topPerformersRecognized,
    String? rewardsOrRituals,
    String? reflectionNotes,
  }) async {
    isSaving.value = true;
    await _runGuarded(() async {
      final res = await _strategyService.finalizeWeek13(
        cycleId,
        overallExecutionScore: overallExecutionScore,
        overallOutcomeScore: overallOutcomeScore,
        okrAchievementRate: okrAchievementRate,
        strategicLearnings: strategicLearnings,
        systemicBlockers: systemicBlockers,
        portfolioAdjustments: portfolioAdjustments,
        nextCycleRecommendations: nextCycleRecommendations,
        celebrationTitle: celebrationTitle,
        milestonesAchieved: milestonesAchieved,
        topPerformersRecognized: topPerformersRecognized,
        rewardsOrRituals: rewardsOrRituals,
        reflectionNotes: reflectionNotes,
      );

      currentWeek13Review.value = res['cycle_review'];
      currentCelebration.value = res['celebration'];
      await loadExecution();
      Get.snackbar(
        'Tuần 13 Hoàn Tất',
        'Chúc mừng! Đã chuyển dịch chiến lược và lưu bản vinh danh chu kỳ 12 tuần',
        snackPosition: SnackPosition.BOTTOM,
        backgroundColor: const Color(0xFF10B981),
        colorText: Colors.white,
      );
    }, showSnackbar: true);
    isSaving.value = false;
  }

  // ====================================================================
  // mCOSA V12 Portfolio Intelligence (Sprint 6)
  // ====================================================================

  Future<void> detectPortfolioNecessity() async {
    await _runGuarded(() async {
      portfolioDetection.value = await _strategyService.detectPortfolioNecessity();
    });
  }

  Future<void> loadPortfolios() async {
    await _runGuarded(() async {
      portfolios.value = await _strategyService.getPortfolios();
      if (portfolios.isNotEmpty && selectedPortfolioId.value == null) {
        await selectPortfolio(portfolios.first['id']);
      }
    });
  }

  Future<void> selectPortfolio(String portfolioId) async {
    selectedPortfolioId.value = portfolioId;
    await Future.wait([
      loadPortfolioProjects(portfolioId),
      loadPortfolioPestel(portfolioId),
      loadPortfolioImpactMatrix(portfolioId),
      loadPortfolioAdvancedData(portfolioId),
      loadPortfolioCycles(portfolioId),
    ]);
  }



  Future<void> loadPortfolioProjects(String portfolioId) async {
    await _runGuarded(() async {
      currentPortfolioProjects.value = await _strategyService.getPortfolioProjects(portfolioId);
    });
  }

  Future<void> loadPortfolioPestel(String portfolioId) async {
    await _runGuarded(() async {
      currentPortfolioPestel.value = await _strategyService.getPortfolioPestel(portfolioId);
    });
  }

  Future<void> loadPortfolioImpactMatrix(String portfolioId) async {
    await _runGuarded(() async {
      currentImpactMatrix.value = await _strategyService.getPortfolioImpactMatrix(portfolioId);
    });
  }

  Future<void> createPortfolio({
    required String name,
    String? description,
    String? strategicFocus,
  }) async {
    isSaving.value = true;
    await _runGuarded(() async {
      final p = await _strategyService.createPortfolio(
        name: name,
        description: description,
        strategicFocus: strategicFocus,
      );
      await loadPortfolios();
      await selectPortfolio(p['id']);
      Get.snackbar(
        'Tạo Danh Mục Thành Công',
        'Đã khởi tạo Portfolio "$name"',
        snackPosition: SnackPosition.BOTTOM,
        backgroundColor: const Color(0xFF10B981),
        colorText: Colors.white,
      );
    }, showSnackbar: true);
    isSaving.value = false;
  }

  Future<void> addProjectToPortfolio(
    String portfolioId, {
    required String projectId,
    String strategicPriority = 'core',
    double capacityAllocation = 0.0,
    double founderAttentionHours = 0.0,
  }) async {
    isSaving.value = true;
    await _runGuarded(() async {
      await _strategyService.addProjectToPortfolio(
        portfolioId,
        projectId: projectId,
        strategicPriority: strategicPriority,
        capacityAllocation: capacityAllocation,
        founderAttentionHours: founderAttentionHours,
      );
      await selectPortfolio(portfolioId);
      Get.snackbar('Thành công', 'Đã thêm dự án vào Portfolio', snackPosition: SnackPosition.BOTTOM, backgroundColor: const Color(0xFF10B981), colorText: Colors.white);
    }, showSnackbar: true);
    isSaving.value = false;
  }

  Future<void> removeProjectFromPortfolio(String portfolioId, String projectId) async {
    isSaving.value = true;
    await _runGuarded(() async {
      await _strategyService.removeProjectFromPortfolio(portfolioId, projectId);
      await selectPortfolio(portfolioId);
      Get.snackbar('Đã xoá', 'Đã gỡ dự án khỏi Portfolio', snackPosition: SnackPosition.BOTTOM);
    }, showSnackbar: true);
    isSaving.value = false;
  }

  Future<void> addPortfolioPestelItem(
    String portfolioId, {
    required String factor,
    required String statement,
    String impact = 'medium',
    String horizon = 'medium',
    String confidence = 'medium',
    String evidenceStatus = 'hypothesis',
  }) async {
    isSaving.value = true;
    await _runGuarded(() async {
      await _strategyService.addPortfolioPestelItem(
        portfolioId,
        factor: factor,
        statement: statement,
        impact: impact,
        horizon: horizon,
        confidence: confidence,
        evidenceStatus: evidenceStatus,
      );
      await selectPortfolio(portfolioId);
      Get.snackbar('Thành công', 'Đã thêm yếu tố PESTEL dùng chung cho Portfolio', snackPosition: SnackPosition.BOTTOM, backgroundColor: const Color(0xFF10B981), colorText: Colors.white);
    }, showSnackbar: true);
    isSaving.value = false;
  }

  Future<void> setProjectPestelImpact(
    String projectId, {
    required String pestelItemId,
    String impactType = 'POSITIVE',
    String impactMagnitude = 'MEDIUM',
    String? impactAnalysis,
    String? mitigationOrLeverage,
  }) async {
    isSaving.value = true;
    await _runGuarded(() async {
      await _strategyService.setProjectPestelImpact(
        projectId,
        pestelItemId: pestelItemId,
        impactType: impactType,
        impactMagnitude: impactMagnitude,
        impactAnalysis: impactAnalysis,
        mitigationOrLeverage: mitigationOrLeverage,
      );
      if (selectedPortfolioId.value != null) {
        await loadPortfolioImpactMatrix(selectedPortfolioId.value!);
      }
      Get.snackbar('Thành công', 'Đã cập nhật ma trận tác động PESTEL của dự án', snackPosition: SnackPosition.BOTTOM, backgroundColor: const Color(0xFF10B981), colorText: Colors.white);
    }, showSnackbar: true);
    isSaving.value = false;
  }

  // ====================================================================
  // mCOSA V12 Sprint 7 Portfolio SWOT, TOWS, Synergies, Dependencies & Options
  // ====================================================================

  Future<void> loadPortfolioAdvancedData(String portfolioId) async {
    await _runGuarded(() async {
      final results = await Future.wait([
        _strategyService.getPortfolioSwot(portfolioId),
        _strategyService.getPortfolioTows(portfolioId),
        _strategyService.getPortfolioSynergies(portfolioId),
        _strategyService.getPortfolioDependencies(portfolioId),
        _strategyService.getPortfolioOptions(portfolioId),
      ]);
      currentPortfolioSwot.value = results[0];
      currentPortfolioTows.value = results[1];
      currentPortfolioSynergies.value = results[2];
      currentPortfolioDependencies.value = results[3];
      currentPortfolioOptions.value = results[4];
    });
  }

  Future<void> addPortfolioSwotItem(
    String portfolioId, {
    required String category,
    required String statement,
  }) async {
    isSaving.value = true;
    await _runGuarded(() async {
      await _strategyService.addPortfolioSwotItem(portfolioId, category: category, statement: statement);
      currentPortfolioSwot.value = await _strategyService.getPortfolioSwot(portfolioId);
      Get.snackbar('Thành công', 'Đã thêm yếu tố SWOT cấp Portfolio', snackPosition: SnackPosition.BOTTOM, backgroundColor: const Color(0xFF10B981), colorText: Colors.white);
    }, showSnackbar: true);
    isSaving.value = false;
  }

  Future<void> addPortfolioTowsOption(
    String portfolioId, {
    required String quadrant,
    required String title,
  }) async {
    isSaving.value = true;
    await _runGuarded(() async {
      await _strategyService.addPortfolioTowsOption(portfolioId, quadrant: quadrant, title: title);
      currentPortfolioTows.value = await _strategyService.getPortfolioTows(portfolioId);
      Get.snackbar('Thành công', 'Đã thêm định hướng TOWS cấp Portfolio', snackPosition: SnackPosition.BOTTOM, backgroundColor: const Color(0xFF10B981), colorText: Colors.white);
    }, showSnackbar: true);
    isSaving.value = false;
  }

  Future<void> addPortfolioSynergy(
    String portfolioId, {
    required String sourceProjectId,
    required String targetProjectId,
    required String synergyType,
    required String description,
    double? estimatedValue,
  }) async {
    isSaving.value = true;
    await _runGuarded(() async {
      await _strategyService.addPortfolioSynergy(
        portfolioId,
        sourceProjectId: sourceProjectId,
        targetProjectId: targetProjectId,
        synergyType: synergyType,
        description: description,
        estimatedValue: estimatedValue,
      );
      currentPortfolioSynergies.value = await _strategyService.getPortfolioSynergies(portfolioId);
      Get.snackbar('Thành công', 'Đã thêm điểm cộng hưởng giữa 2 dự án', snackPosition: SnackPosition.BOTTOM, backgroundColor: const Color(0xFF10B981), colorText: Colors.white);
    }, showSnackbar: true);
    isSaving.value = false;
  }

  Future<void> deletePortfolioSynergy(String portfolioId, String synergyId) async {
    isSaving.value = true;
    await _runGuarded(() async {
      await _strategyService.deletePortfolioSynergy(portfolioId, synergyId);
      currentPortfolioSynergies.value = await _strategyService.getPortfolioSynergies(portfolioId);
      Get.snackbar('Thành công', 'Đã xóa quan hệ cộng hưởng', snackPosition: SnackPosition.BOTTOM, backgroundColor: const Color(0xFF10B981), colorText: Colors.white);
    }, showSnackbar: true);
    isSaving.value = false;
  }

  Future<void> addPortfolioDependency(
    String portfolioId, {
    required String predecessorProjectId,
    required String successorProjectId,
    required String dependencyType,
    String? description,
  }) async {
    isSaving.value = true;
    await _runGuarded(() async {
      await _strategyService.addPortfolioDependency(
        portfolioId,
        predecessorProjectId: predecessorProjectId,
        successorProjectId: successorProjectId,
        dependencyType: dependencyType,
        description: description,
      );
      currentPortfolioDependencies.value = await _strategyService.getPortfolioDependencies(portfolioId);
      Get.snackbar('Thành công', 'Đã ghi nhận phụ thuộc giữa các dự án', snackPosition: SnackPosition.BOTTOM, backgroundColor: const Color(0xFF10B981), colorText: Colors.white);
    }, showSnackbar: true);
    isSaving.value = false;
  }

  Future<void> deletePortfolioDependency(String portfolioId, String dependencyId) async {
    isSaving.value = true;
    await _runGuarded(() async {
      await _strategyService.deletePortfolioDependency(portfolioId, dependencyId);
      currentPortfolioDependencies.value = await _strategyService.getPortfolioDependencies(portfolioId);
      Get.snackbar('Thành công', 'Đã xóa quan hệ phụ thuộc', snackPosition: SnackPosition.BOTTOM, backgroundColor: const Color(0xFF10B981), colorText: Colors.white);
    }, showSnackbar: true);
    isSaving.value = false;
  }

  Future<void> createPortfolioOption(
    String portfolioId, {
    required String title,
    String? description,
    double strategicFitScore = 0.8,
    double feasibilityScore = 0.7,
    String riskLevel = 'MEDIUM',
  }) async {
    isSaving.value = true;
    await _runGuarded(() async {
      await _strategyService.createPortfolioOption(
        portfolioId,
        title: title,
        description: description,
        strategicFitScore: strategicFitScore,
        feasibilityScore: feasibilityScore,
        riskLevel: riskLevel,
      );
      currentPortfolioOptions.value = await _strategyService.getPortfolioOptions(portfolioId);
      Get.snackbar('Thành công', 'Đã thêm Tùy Chọn Chiến Lược (Portfolio Option)', snackPosition: SnackPosition.BOTTOM, backgroundColor: const Color(0xFF10B981), colorText: Colors.white);
    }, showSnackbar: true);
    isSaving.value = false;
  }

  Future<void> updatePortfolioOptionStatus(
    String portfolioId,
    String optionId,
    String newStatus,
  ) async {
    isSaving.value = true;
    await _runGuarded(() async {
      await _strategyService.updatePortfolioOption(portfolioId, optionId, status: newStatus);
      currentPortfolioOptions.value = await _strategyService.getPortfolioOptions(portfolioId);
      Get.snackbar('Thành công', 'Đã cập nhật trạng thái tùy chọn chiến lược', snackPosition: SnackPosition.BOTTOM, backgroundColor: const Color(0xFF10B981), colorText: Colors.white);
    }, showSnackbar: true);
    isSaving.value = false;
  }

  // ====================================================================
  // mCOSA V12 Sprint 8 Portfolio Cycles & Founder WIP Limit Methods
  // ====================================================================

  Future<void> loadFounderProfile() async {
    await _runGuarded(() async {
      founderProfile.value = await _strategyService.getFounderProfile();
    });
  }

  Future<void> updateFounderProfile({
    double? weeklyCapacityHours,
    int? maxActiveStrategicProjects,
  }) async {
    isSaving.value = true;
    await _runGuarded(() async {
      founderProfile.value = await _strategyService.updateFounderProfile(
        weeklyCapacityHours: weeklyCapacityHours,
        maxActiveStrategicProjects: maxActiveStrategicProjects,
      );
      Get.snackbar('Thành công', 'Đã cập nhật cấu hình WIP Limit và năng lực Founder', snackPosition: SnackPosition.BOTTOM, backgroundColor: const Color(0xFF10B981), colorText: Colors.white);
    }, showSnackbar: true);
    isSaving.value = false;
  }

  Future<void> loadPortfolioCycles(String portfolioId) async {
    await _runGuarded(() async {
      currentPortfolioCycles.value = await _strategyService.getPortfolioCycles(portfolioId);
    });
  }

  Future<void> createPortfolioCycle(
    String portfolioId, {
    required String title,
  }) async {
    isSaving.value = true;
    await _runGuarded(() async {
      await _strategyService.createPortfolioCycle(portfolioId, title: title);
      currentPortfolioCycles.value = await _strategyService.getPortfolioCycles(portfolioId);
      Get.snackbar('Thành công', 'Đã khởi tạo chu kỳ danh mục "$title"', snackPosition: SnackPosition.BOTTOM, backgroundColor: const Color(0xFF10B981), colorText: Colors.white);
    }, showSnackbar: true);
    isSaving.value = false;
  }

  Future<void> activatePortfolioCycle(String portfolioId, String cycleId) async {
    isSaving.value = true;
    await _runGuarded(() async {
      await _strategyService.activatePortfolioCycle(cycleId);
      currentPortfolioCycles.value = await _strategyService.getPortfolioCycles(portfolioId);
      Get.snackbar('Thành công', 'Kích hoạt Chu kỳ Portfolio 12WY thành công! Đã kiểm tra tuân thủ WIP Limit.', snackPosition: SnackPosition.BOTTOM, backgroundColor: const Color(0xFF10B981), colorText: Colors.white);
    }, showSnackbar: true);
    isSaving.value = false;
  }

  // ====================================================================
  // mCOSA V12 Sprint 9 Next Best Action Engine Methods (Spec §37)
  // ====================================================================

  Future<void> loadCeoNextActions() async {
    await _runGuarded(() async {
      ceoNextActions.value = await _strategyService.getCeoNextActions(limit: 5);
    });
  }

  Future<void> evaluateCeoNextActions({String? projectId, String? portfolioId}) async {
    isSaving.value = true;
    await _runGuarded(() async {
      final rankings = await _strategyService.evaluateCeoNextActions(projectId: projectId, portfolioId: portfolioId);
      if (rankings.isNotEmpty) {
        ceoNextActions.value = rankings.map((r) => r['candidate']).toList();
      } else {
        await loadCeoNextActions();
      }
      Get.snackbar('Thành công', 'Đã xếp hạng lại danh sách Next Best Actions (R0 Formula)', snackPosition: SnackPosition.BOTTOM, backgroundColor: const Color(0xFF10B981), colorText: Colors.white);
    }, showSnackbar: true);
    isSaving.value = false;
  }

  Future<void> updateNextActionStatus(String actionId, String newStatus) async {
    isSaving.value = true;
    await _runGuarded(() async {
      await _strategyService.updateNextActionStatus(actionId, newStatus);
      await loadCeoNextActions();
      Get.snackbar('Thành công', 'Đã cập nhật trạng thái hành động tiếp theo', snackPosition: SnackPosition.BOTTOM, backgroundColor: const Color(0xFF10B981), colorText: Colors.white);
    }, showSnackbar: true);
    isSaving.value = false;
  }

  // ====================================================================
  // mCOSA V12 Sprint 10 Living PESTEL & Model Profiles Methods (Spec §48, §56)
  // ====================================================================

  Future<void> loadPestelSignals() async {
    await _runGuarded(() async {
      pestelSignals.value = await _strategyService.getPestelSignals();
    });
  }

  Future<void> ingestPestelSignal({
    required String signalTitle,
    required String pestelCategory,
    required String magnitude,
    String? signalSummary,
  }) async {
    isSaving.value = true;
    await _runGuarded(() async {
      final res = await _strategyService.ingestPestelSignal(
        signalTitle: signalTitle,
        pestelCategory: pestelCategory,
        magnitude: magnitude,
        signalSummary: signalSummary,
      );
      await loadPestelSignals();
      if (res['ceo_exception_created'] == true) {
        Get.snackbar('Cảnh báo Material Change', 'Tín hiệu vĩ mô trọng yếu đã tự động tạo CEO Exception trong Next Best Actions', snackPosition: SnackPosition.BOTTOM, backgroundColor: const Color(0xFFF59E0B), colorText: Colors.white);
      } else {
        Get.snackbar('Thành công', 'Đã ghi nhận tín hiệu Living PESTEL', snackPosition: SnackPosition.BOTTOM, backgroundColor: const Color(0xFF10B981), colorText: Colors.white);
      }
    }, showSnackbar: true);
    isSaving.value = false;
  }

  Future<void> loadModelRunsAudit() async {
    await _runGuarded(() async {
      modelRunsAudit.value = await _strategyService.getModelRunsAudit(limit: 20);
    });
  }

  Future<void> loadModelProfiles() async {
    await _runGuarded(() async {
      modelProfiles.value = await _strategyService.getModelProfiles();
    });
  }

  Future<void> updateModelProfile(
    String profileId, {
    String? displayName,
    double? temperature,
    bool? isActive,
  }) async {
    isSaving.value = true;
    await _runGuarded(() async {
      await _strategyService.updateModelProfile(
        profileId,
        displayName: displayName,
        temperature: temperature,
        isActive: isActive,
      );
      await loadModelProfiles();
      Get.snackbar('Thành công', 'Đã cập nhật cấu hình Model Profile', snackPosition: SnackPosition.BOTTOM, backgroundColor: const Color(0xFF10B981), colorText: Colors.white);
    }, showSnackbar: true);
    isSaving.value = false;
  }
}








