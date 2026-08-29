import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../../services/strategy_service.dart';

mixin GovernanceStateMixin on GetxController {
  StrategyService get strategyService;
  RxBool get isSaving;

  Future<void> runGuarded(Future<void> Function() action, {bool showSnackbar = false});
  Future<void> loadProjects();

  final cycleStages = <dynamic>[].obs;
  final milestones = <dynamic>[].obs;
  final cycleContract = Rxn<Map<String, dynamic>>();
  final gateDecisions = <dynamic>[].obs;
  final cycleCompilationStatus = Rxn<Map<String, dynamic>>();
  final week13Readiness = Rxn<Map<String, dynamic>>();

  Future<void> loadCycleGovernance(String cycleId) async {
    await runGuarded(() async {
      cycleStages.value = await strategyService.getCycleStages(cycleId);
      milestones.value = await strategyService.getMilestones(cycleId: cycleId);
      cycleContract.value = await strategyService.getCycleContract(cycleId);
      gateDecisions.value = await strategyService.getGateDecisions();
    });
  }

  Future<void> generateStandardStages(String cycleId) async {
    isSaving.value = true;
    await runGuarded(() async {
      cycleStages.value = await strategyService.generateStandardCycleStages(cycleId);
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
    await runGuarded(() async {
      await strategyService.recordGateDecision(
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

  Future<void> saveCycleContract({
    required String cycleId,
    required String successDefinition,
    double? founderCapacityHours,
    double? riskBufferPercent,
  }) async {
    isSaving.value = true;
    await runGuarded(() async {
      final res = await strategyService.upsertCycleContract(
        cycleId,
        successDefinition: successDefinition,
        founderCapacityPerWeek: founderCapacityHours,
        reservedBufferPercent: riskBufferPercent,
        status: 'approved',
      );
      cycleContract.value = res;
      Get.snackbar('Thành công', 'Đã lưu hợp đồng cam kết chu kỳ 12 tuần', snackPosition: SnackPosition.BOTTOM, backgroundColor: const Color(0xFF10B981), colorText: Colors.white);
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
    await saveCycleContract(
      cycleId: cycleId,
      successDefinition: successDefinition,
      founderCapacityHours: founderCapacityPerWeek,
      riskBufferPercent: reservedBufferPercent,
    );
  }

  Future<void> loadCycleCompilationStatus(String cycleId) async {
    await runGuarded(() async {
      cycleCompilationStatus.value = await strategyService.getCycleCompilationStatus(cycleId);
    });
  }

  Future<void> compileCycle(String cycleId) async {
    isSaving.value = true;
    await runGuarded(() async {
      final res = await strategyService.compileCycle(cycleId);
      cycleCompilationStatus.value = res;
      Get.snackbar('Hoàn tất biên dịch', 'Đã biên dịch thành công chu kỳ sang Runtime V10', snackPosition: SnackPosition.BOTTOM, backgroundColor: const Color(0xFF10B981), colorText: Colors.white);
    }, showSnackbar: true);
    isSaving.value = false;
  }

  Future<void> compileWeeklyPlan(String planId) async {
    isSaving.value = true;
    await runGuarded(() async {
      await strategyService.compileWeeklyPlan(planId);
      Get.snackbar('Hoàn tất', 'Đã biên dịch kế hoạch tuần sang danh mục Tasks', snackPosition: SnackPosition.BOTTOM, backgroundColor: const Color(0xFF10B981), colorText: Colors.white);
    }, showSnackbar: true);
    isSaving.value = false;
  }

  Future<void> createWeeklyReview(
    String cycleId, {
    required String weeklyPlanId,
    required double executionScore,
    required double outcomeScore,
    String? evidenceLearned,
    String? narrativeSummary,
    String? recommendation,
  }) async {
    isSaving.value = true;
    await runGuarded(() async {
      await strategyService.createWeeklyReview(
        cycleId,
        weeklyPlanId: weeklyPlanId,
        executionScore: executionScore,
        outcomeScore: outcomeScore,
        evidenceLearned: evidenceLearned,
        narrativeSummary: narrativeSummary,
        recommendation: recommendation,
      );
      Get.snackbar('Đánh giá đã lưu', 'Đã ghi nhận Weekly Review và lưu vết bài học kinh nghiệm', snackPosition: SnackPosition.BOTTOM, backgroundColor: const Color(0xFF10B981), colorText: Colors.white);
    }, showSnackbar: true);
    isSaving.value = false;
  }

  Future<void> loadWeek13Readiness(String cycleId) async {
    await runGuarded(() async {
      week13Readiness.value = await strategyService.getWeek13Readiness(cycleId);
    });
  }

  Future<void> finalizeWeek13(
    String cycleId, {
    required double overallExecutionScore,
    required double overallOutcomeScore,
    required double okrAchievementRate,
    required String celebrationTitle,
    String? strategicLearnings,
    String? rewardsOrRituals,
  }) async {
    isSaving.value = true;
    await runGuarded(() async {
      await strategyService.finalizeWeek13(
        cycleId,
        overallExecutionScore: overallExecutionScore,
        overallOutcomeScore: overallOutcomeScore,
        okrAchievementRate: okrAchievementRate,
        celebrationTitle: celebrationTitle,
        strategicLearnings: strategicLearnings,
        rewardsOrRituals: rewardsOrRituals,
      );
      Get.snackbar('Tuần 13 hoàn tất', 'Chu kỳ đã hoàn thành xuất sắc và sẵn sàng cho chu kỳ tiếp theo', snackPosition: SnackPosition.BOTTOM, backgroundColor: Colors.pinkAccent, colorText: Colors.white);
    }, showSnackbar: true);
    isSaving.value = false;
  }
}
