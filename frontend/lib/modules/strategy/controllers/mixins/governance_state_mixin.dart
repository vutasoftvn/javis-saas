import 'package:get/get.dart';
import '../../../../core/widgets/app_toast.dart';
import '../../services/strategy_service.dart';

mixin GovernanceStateMixin on GetxController {
  StrategyService get strategyService;
  RxBool get isSaving;
  RxnString get errorMessage;

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
      final stagesResult = await strategyService.getCycleStages(cycleId);
      cycleStages.value = stagesResult.items;
      if (stagesResult.errorMessage != null) errorMessage.value = stagesResult.errorMessage;

      final milestonesResult = await strategyService.getMilestones(cycleId: cycleId);
      milestones.value = milestonesResult.items;
      if (milestonesResult.errorMessage != null) errorMessage.value = milestonesResult.errorMessage;

      cycleContract.value = await strategyService.getCycleContract(cycleId);

      final gateDecisionsResult = await strategyService.getGateDecisions();
      gateDecisions.value = gateDecisionsResult.items;
      if (gateDecisionsResult.errorMessage != null) errorMessage.value = gateDecisionsResult.errorMessage;
    });
  }

  Future<void> generateStandardStages(String cycleId) async {
    isSaving.value = true;
    await runGuarded(() async {
      final result = await strategyService.generateStandardCycleStages(cycleId);
      cycleStages.value = result.items;
      if (result.errorMessage != null) {
        errorMessage.value = result.errorMessage;
      } else {
        AppToast.success(
          'Đã tạo 5 giai đoạn chuẩn (13-Week Stages) cho chu kỳ',
          title: 'Thành công',
        );
      }
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
      AppToast.success(
        'Cổng kiểm soát ghi nhận quyết định: $decision',
        title: 'Quyết định Cổng đã lưu',
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
      AppToast.success('Đã lưu hợp đồng cam kết chu kỳ 12 tuần');
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
      AppToast.success(
        'Đã biên dịch thành công chu kỳ sang Runtime V10',
        title: 'Hoàn tất biên dịch',
      );
    }, showSnackbar: true);
    isSaving.value = false;
  }

  Future<void> compileWeeklyPlan(String planId) async {
    isSaving.value = true;
    await runGuarded(() async {
      await strategyService.compileWeeklyPlan(planId);
      AppToast.success(
        'Đã biên dịch kế hoạch tuần sang danh mục Tasks',
        title: 'Hoàn tất',
      );
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
      AppToast.success(
        'Đã ghi nhận Weekly Review và lưu vết bài học kinh nghiệm',
        title: 'Đánh giá đã lưu',
      );
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
      AppToast.success(
        'Chu kỳ đã hoàn thành xuất sắc và sẵn sàng cho chu kỳ tiếp theo',
        title: 'Tuần 13 hoàn tất',
      );
    }, showSnackbar: true);
    isSaving.value = false;
  }
}
