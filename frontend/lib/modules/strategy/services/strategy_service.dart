export 'strategy_service_base.dart';
export 'canvas_service.dart';
export 'okr_service.dart';
export 'twelve_week_service.dart';
export 'project_service.dart';
export 'portfolio_service.dart';
export 'founder_service.dart';

import '../models/strategy_list_result.dart';
import 'strategy_service_base.dart';
import 'canvas_service.dart';
import 'okr_service.dart';
import 'twelve_week_service.dart';
import 'project_service.dart';
import 'portfolio_service.dart';
import 'founder_service.dart';

/// Facade StrategyService delegating to specialized domain services.
/// Preserves 100% backward compatibility for all existing callers.
class StrategyService extends StrategyServiceBase {
  final CanvasService _canvasService;
  final OkrService _okrService;
  final TwelveWeekService _twelveWeekService;
  final ProjectService _projectService;
  final PortfolioService _portfolioService;
  final FounderService _founderService;

  StrategyService({
    CanvasService? canvasService,
    OkrService? okrService,
    TwelveWeekService? twelveWeekService,
    ProjectService? projectService,
    PortfolioService? portfolioService,
    FounderService? founderService,
  })  : _canvasService = canvasService ?? CanvasService(),
        _okrService = okrService ?? OkrService(),
        _twelveWeekService = twelveWeekService ?? TwelveWeekService(),
        _projectService = projectService ?? ProjectService(),
        _portfolioService = portfolioService ?? PortfolioService(),
        _founderService = founderService ?? FounderService();

  // ====================================================================
  // Strategic Canvas & Foundation (delegated to CanvasService)
  // ====================================================================

  Future<StrategyListResult<Map<String, dynamic>>> getCanvases() => _canvasService.getCanvases();

  Future<Map<String, dynamic>> getCanvasDetail(String canvasId) => _canvasService.getCanvasDetail(canvasId);

  Future<Map<String, dynamic>> createCanvas(String name, {String? description}) =>
      _canvasService.createCanvas(name, description: description);

  Future<Map<String, dynamic>> updateCanvas(String canvasId, {String? name, String? description}) =>
      _canvasService.updateCanvas(canvasId, name: name, description: description);

  Future<void> deleteCanvas(String canvasId) => _canvasService.deleteCanvas(canvasId);

  Future<Map<String, dynamic>> generateAiFoundation(String canvasId) =>
      _canvasService.generateAiFoundation(canvasId);

  Future<Map<String, dynamic>> createRevision(String canvasId, {String? baseRevisionId}) =>
      _canvasService.createRevision(canvasId, baseRevisionId: baseRevisionId);

  Future<Map<String, dynamic>> getRevisionDetail(String revisionId) =>
      _canvasService.getRevisionDetail(revisionId);

  Future<Map<String, dynamic>> submitReview(String revisionId) =>
      _canvasService.submitReview(revisionId);

  Future<Map<String, dynamic>> approveRevision(String revisionId, {String? note}) =>
      _canvasService.approveRevision(revisionId, note: note);

  Future<Map<String, dynamic>> requestChanges(String revisionId, String reason) =>
      _canvasService.requestChanges(revisionId, reason);

  Future<Map<String, dynamic>> saveFoundation(
    String revisionId, {
    required String vision,
    required String mission,
    required List<Map<String, dynamic>> values,
  }) =>
      _canvasService.saveFoundation(revisionId, vision: vision, mission: mission, values: values);

  // ====================================================================
  // OKRs & Key Results (delegated to OkrService)
  // ====================================================================

  Future<StrategyListResult<Map<String, dynamic>>> getOkrCycles() => _okrService.getOkrCycles();

  Future<Map<String, dynamic>> createOkrCycle({
    required String name,
    DateTime? startDate,
    DateTime? endDate,
    String? status,
  }) =>
      _okrService.createOkrCycle(name: name, startDate: startDate, endDate: endDate, status: status);

  Future<StrategyListResult<Map<String, dynamic>>> getObjectives({String? cycleId}) =>
      _okrService.getObjectives(cycleId: cycleId);

  Future<Map<String, dynamic>> createObjective({
    required String title,
    String? cycleId,
    String? status,
  }) =>
      _okrService.createObjective(title: title, cycleId: cycleId, status: status);

  Future<Map<String, dynamic>> updateObjective(
    String objectiveId, {
    String? title,
    String? status,
  }) =>
      _okrService.updateObjective(objectiveId, title: title, status: status);

  Future<void> deleteObjective(String objectiveId) => _okrService.deleteObjective(objectiveId);

  Future<StrategyListResult<Map<String, dynamic>>> getKeyResults({String? objectiveId}) =>
      _okrService.getKeyResults(objectiveId: objectiveId);

  Future<Map<String, dynamic>> createKeyResult({
    required String objectiveId,
    String? title,
    double? baselineValue,
    double? currentValue,
    double? targetValue,
    String? unit,
    String? cadence,
    String? status,
  }) =>
      _okrService.createKeyResult(
        objectiveId: objectiveId,
        title: title,
        baselineValue: baselineValue,
        currentValue: currentValue,
        targetValue: targetValue,
        unit: unit,
        cadence: cadence,
        status: status,
      );

  Future<Map<String, dynamic>> updateKeyResult(
    String keyResultId, {
    double? currentValue,
    double? targetValue,
    String? unit,
    String? status,
  }) =>
      _okrService.updateKeyResult(
        keyResultId,
        currentValue: currentValue,
        targetValue: targetValue,
        unit: unit,
        status: status,
      );

  Future<void> deleteKeyResult(String keyResultId) => _okrService.deleteKeyResult(keyResultId);

  Future<Map<String, dynamic>> generateAiOkrs({
    String? towsId,
    int objectivesCount = 2,
    int krsPerObjectiveCount = 3,
    String? cycleId,
  }) =>
      _okrService.generateAiOkrs(
        towsId: towsId,
        objectivesCount: objectivesCount,
        krsPerObjectiveCount: krsPerObjectiveCount,
        cycleId: cycleId,
      );

  // ====================================================================
  // 12-Week Execution (delegated to TwelveWeekService)
  // ====================================================================

  Future<StrategyListResult<Map<String, dynamic>>> getTwelveWeekCycles() =>
      _twelveWeekService.getTwelveWeekCycles();

  Future<Map<String, dynamic>> createTwelveWeekCycle({
    required String theme,
    String? projectId,
    int? durationWeeks,
    DateTime? startDate,
    DateTime? endDate,
  }) =>
      _twelveWeekService.createTwelveWeekCycle(
        theme: theme,
        projectId: projectId,
        durationWeeks: durationWeeks,
        startDate: startDate,
        endDate: endDate,
      );

  Future<Map<String, dynamic>> getCycleTimeline(String cycleId) =>
      _twelveWeekService.getCycleTimeline(cycleId);

  Future<StrategyListResult<Map<String, dynamic>>> getWeeklyPlans({String? cycleId}) =>
      _twelveWeekService.getWeeklyPlans(cycleId: cycleId);

  Future<Map<String, dynamic>> createWeeklyPlan({
    required int weekNo,
    String? cycleId,
    String? focus,
    DateTime? startDate,
    DateTime? endDate,
  }) =>
      _twelveWeekService.createWeeklyPlan(
        weekNo: weekNo,
        cycleId: cycleId,
        focus: focus,
        startDate: startDate,
        endDate: endDate,
      );

  Future<Map<String, dynamic>> updateWeeklyPlan(
    String planId, {
    String? focus,
    double? executionScore,
    String? reflection,
    DateTime? startDate,
    DateTime? endDate,
  }) =>
      _twelveWeekService.updateWeeklyPlan(
        planId,
        focus: focus,
        executionScore: executionScore,
        reflection: reflection,
        startDate: startDate,
        endDate: endDate,
      );

  Future<StrategyListResult<Map<String, dynamic>>> getWeeklyCommitments({String? weeklyPlanId}) =>
      _twelveWeekService.getWeeklyCommitments(weeklyPlanId: weeklyPlanId);

  Future<Map<String, dynamic>> createWeeklyCommitment({
    required String weeklyPlanId,
    required String title,
    String? plannedEffort,
    String? status,
  }) =>
      _twelveWeekService.createWeeklyCommitment(
        weeklyPlanId: weeklyPlanId,
        title: title,
        plannedEffort: plannedEffort,
        status: status,
      );

  Future<Map<String, dynamic>> updateWeeklyCommitment(
    String commitmentId, {
    String? title,
    String? status,
    String? plannedEffort,
  }) =>
      _twelveWeekService.updateWeeklyCommitment(
        commitmentId,
        title: title,
        status: status,
        plannedEffort: plannedEffort,
      );

  Future<void> deleteWeeklyCommitment(String commitmentId) =>
      _twelveWeekService.deleteWeeklyCommitment(commitmentId);

  Future<StrategyListResult<Map<String, dynamic>>> getCycleStages(String cycleId) =>
      _twelveWeekService.getCycleStages(cycleId);

  Future<StrategyListResult<Map<String, dynamic>>> generateStandardCycleStages(String cycleId) =>
      _twelveWeekService.generateStandardCycleStages(cycleId);

  Future<Map<String, dynamic>> createCycleStage(
    String cycleId, {
    required String name,
    required int startWeek,
    required int endWeek,
    required int orderNo,
    String? purpose,
    Map<String, dynamic>? expectedOutcomes,
  }) =>
      _twelveWeekService.createCycleStage(
        cycleId,
        name: name,
        startWeek: startWeek,
        endWeek: endWeek,
        orderNo: orderNo,
        purpose: purpose,
        expectedOutcomes: expectedOutcomes,
      );

  Future<Map<String, dynamic>> updateCycleStage(
    String stageId, {
    String? name,
    String? purpose,
    int? startWeek,
    int? endWeek,
    String? status,
    Map<String, dynamic>? expectedOutcomes,
  }) =>
      _twelveWeekService.updateCycleStage(
        stageId,
        name: name,
        purpose: purpose,
        startWeek: startWeek,
        endWeek: endWeek,
        status: status,
        expectedOutcomes: expectedOutcomes,
      );

  Future<void> deleteCycleStage(String stageId) => _twelveWeekService.deleteCycleStage(stageId);

  Future<StrategyListResult<Map<String, dynamic>>> getMilestones({
    String? cycleId,
    String? stageId,
    String? projectId,
  }) =>
      _twelveWeekService.getMilestones(cycleId: cycleId, stageId: stageId, projectId: projectId);

  Future<Map<String, dynamic>> createMilestone({
    required String name,
    String? cycleId,
    String? stageId,
    String? projectId,
    String? description,
    int? dueWeek,
    String? acceptanceCriteria,
    Map<String, dynamic>? requiredArtifacts,
    Map<String, dynamic>? requiredMetrics,
  }) =>
      _twelveWeekService.createMilestone(
        name: name,
        cycleId: cycleId,
        stageId: stageId,
        projectId: projectId,
        description: description,
        dueWeek: dueWeek,
        acceptanceCriteria: acceptanceCriteria,
        requiredArtifacts: requiredArtifacts,
        requiredMetrics: requiredMetrics,
      );

  Future<Map<String, dynamic>> updateMilestone(
    String milestoneId, {
    String? name,
    String? description,
    int? dueWeek,
    String? status,
    String? acceptanceCriteria,
  }) =>
      _twelveWeekService.updateMilestone(
        milestoneId,
        name: name,
        description: description,
        dueWeek: dueWeek,
        status: status,
        acceptanceCriteria: acceptanceCriteria,
      );

  Future<void> deleteMilestone(String milestoneId) => _twelveWeekService.deleteMilestone(milestoneId);

  Future<Map<String, dynamic>> linkMilestoneEvidence(
    String milestoneId,
    String evidenceId, {
    String? relevanceNote,
  }) =>
      _twelveWeekService.linkMilestoneEvidence(milestoneId, evidenceId, relevanceNote: relevanceNote);

  Future<void> unlinkMilestoneEvidence(String milestoneId, String evidenceId) =>
      _twelveWeekService.unlinkMilestoneEvidence(milestoneId, evidenceId);

  Future<StrategyListResult<Map<String, dynamic>>> getGateDecisions({
    String? projectId,
    String? stageId,
    String? milestoneId,
  }) =>
      _twelveWeekService.getGateDecisions(projectId: projectId, stageId: stageId, milestoneId: milestoneId);

  Future<Map<String, dynamic>> recordGateDecision({
    required String projectId,
    required String decision,
    required String rationale,
    String? milestoneId,
    String? stageId,
    String? evidenceSummary,
    String? nextStepInstructions,
  }) =>
      _twelveWeekService.recordGateDecision(
        projectId: projectId,
        decision: decision,
        rationale: rationale,
        milestoneId: milestoneId,
        stageId: stageId,
        evidenceSummary: evidenceSummary,
        nextStepInstructions: nextStepInstructions,
      );

  Future<Map<String, dynamic>?> getCycleContract(String cycleId) =>
      _twelveWeekService.getCycleContract(cycleId);

  Future<Map<String, dynamic>> upsertCycleContract(
    String cycleId, {
    required String successDefinition,
    double? founderCapacityPerWeek,
    double? reservedBufferPercent,
    double? aiBudget,
    double? operatingBudget,
    List<String>? goalIds,
    List<String>? krIds,
    String? status,
  }) =>
      _twelveWeekService.upsertCycleContract(
        cycleId,
        successDefinition: successDefinition,
        founderCapacityPerWeek: founderCapacityPerWeek,
        reservedBufferPercent: reservedBufferPercent,
        aiBudget: aiBudget,
        operatingBudget: operatingBudget,
        goalIds: goalIds,
        krIds: krIds,
        status: status,
      );

  Future<Map<String, dynamic>> updateWeeklyMission(
    String planId, {
    String? mission,
    Map<String, dynamic>? successCriteria,
    String? stageId,
    double? outcomeScore,
  }) =>
      _twelveWeekService.updateWeeklyMission(
        planId,
        mission: mission,
        successCriteria: successCriteria,
        stageId: stageId,
        outcomeScore: outcomeScore,
      );

  Future<Map<String, dynamic>> compileCycle(String cycleId) =>
      _twelveWeekService.compileCycle(cycleId);

  Future<Map<String, dynamic>> compileWeeklyPlan(String planId) =>
      _twelveWeekService.compileWeeklyPlan(planId);

  Future<Map<String, dynamic>> getCycleCompilationStatus(String cycleId) =>
      _twelveWeekService.getCycleCompilationStatus(cycleId);

  Future<Map<String, dynamic>> createWeeklyReview(
    String cycleId, {
    required String weeklyPlanId,
    required double executionScore,
    required double outcomeScore,
    String? evidenceLearned,
    Map<String, dynamic>? assumptionsConfirmed,
    Map<String, dynamic>? assumptionsInvalidated,
    String? recommendation,
    String? narrativeSummary,
  }) =>
      _twelveWeekService.createWeeklyReview(
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

  Future<StrategyListResult<Map<String, dynamic>>> getWeeklyReviews(String cycleId) =>
      _twelveWeekService.getWeeklyReviews(cycleId);

  Future<Map<String, dynamic>?> getWeeklyPlanReview(String planId) =>
      _twelveWeekService.getWeeklyPlanReview(planId);

  Future<Map<String, dynamic>> finalizeWeek13(
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
  }) =>
      _twelveWeekService.finalizeWeek13(
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

  Future<Map<String, dynamic>?> getWeek13Review(String cycleId) =>
      _twelveWeekService.getWeek13Review(cycleId);

  Future<Map<String, dynamic>?> getWeek13Celebration(String cycleId) =>
      _twelveWeekService.getWeek13Celebration(cycleId);

  Future<Map<String, dynamic>> getWeek13Readiness(String cycleId) =>
      _twelveWeekService.getWeek13Readiness(cycleId);

  // ====================================================================
  // Strategic Projects & Initiatives (delegated to ProjectService)
  // ====================================================================

  Future<StrategyListResult<Map<String, dynamic>>> getProjects() => _projectService.getProjects();

  Future<Map<String, dynamic>> createProject({
    required String title,
    String? description,
    String? phase,
    String? projectStage,
    String? stageGoal,
    String? currentGate,
    String? status,
    DateTime? startDate,
    DateTime? endDate,
  }) =>
      _projectService.createProject(
        title: title,
        description: description,
        phase: phase,
        projectStage: projectStage,
        stageGoal: stageGoal,
        currentGate: currentGate,
        status: status,
        startDate: startDate,
        endDate: endDate,
      );

  Future<Map<String, dynamic>> updateProject(
    String projectId, {
    String? title,
    String? phase,
    String? currentGate,
    String? status,
    DateTime? startDate,
    DateTime? endDate,
  }) =>
      _projectService.updateProject(
        projectId,
        title: title,
        phase: phase,
        currentGate: currentGate,
        status: status,
        startDate: startDate,
        endDate: endDate,
      );

  Future<void> deleteProject(String projectId) => _projectService.deleteProject(projectId);

  Future<StrategyListResult<Map<String, dynamic>>> getInitiatives({String? projectId}) =>
      _projectService.getInitiatives(projectId: projectId);

  Future<Map<String, dynamic>> createInitiative({
    required String title,
    String? projectId,
    String? status,
  }) =>
      _projectService.createInitiative(title: title, projectId: projectId, status: status);

  Future<Map<String, dynamic>> updateInitiative(
    String initiativeId, {
    String? title,
    String? status,
  }) =>
      _projectService.updateInitiative(initiativeId, title: title, status: status);

  Future<void> deleteInitiative(String initiativeId) =>
      _projectService.deleteInitiative(initiativeId);

  Future<Map<String, dynamic>> classifyProject(
    String projectId, {
    String? titleOverride,
    String? descriptionOverride,
  }) =>
      _projectService.classifyProject(
        projectId,
        titleOverride: titleOverride,
        descriptionOverride: descriptionOverride,
      );

  Future<Map<String, dynamic>> getMethodologyPlan(String projectId) =>
      _projectService.getMethodologyPlan(projectId);

  Future<Map<String, dynamic>> routeMethodology(
    String projectId, {
    List<String>? customMethodologies,
    String? rationaleOverride,
  }) =>
      _projectService.routeMethodology(
        projectId,
        customMethodologies: customMethodologies,
        rationaleOverride: rationaleOverride,
      );

  Future<Map<String, dynamic>> exportAnalysisPrompt({
    String? projectId,
    String? canvasId,
  }) =>
      _projectService.exportAnalysisPrompt(projectId: projectId, canvasId: canvasId);

  Future<Map<String, dynamic>> importAnalysisResult(
    String rawInput, {
    String? projectId,
    String? canvasId,
  }) =>
      _projectService.importAnalysisResult(rawInput, projectId: projectId, canvasId: canvasId);

  Future<StrategyListResult<Map<String, dynamic>>> getWorkspaceTemplates() =>
      _projectService.getWorkspaceTemplates();

  Future<StrategyListResult<Map<String, dynamic>>> provisionWorkspaceTemplates() =>
      _projectService.provisionWorkspaceTemplates();

  Future<Map<String, dynamic>> resetWorkspaceTemplate(String templateId) =>
      _projectService.resetWorkspaceTemplate(templateId);

  Future<Map<String, dynamic>> updateWorkspaceTemplate(
    String templateId, {
    String? name,
    List<dynamic>? capabilities,
  }) =>
      _projectService.updateWorkspaceTemplate(templateId, name: name, capabilities: capabilities);

  Future<StrategyListResult<Map<String, dynamic>>> getProjectStages(String projectId) =>
      _projectService.getProjectStages(projectId);

  Future<Map<String, dynamic>> generateMvpRoadmap(String projectId, {String? instruction}) =>
      _projectService.generateMvpRoadmap(projectId, instruction: instruction);

  Future<Map<String, dynamic>> saveMvpRoadmapDraft(String projectId, List<Map<String, dynamic>> stages) =>
      _projectService.saveMvpRoadmapDraft(projectId, stages);

  Future<Map<String, dynamic>> confirmMvpRoadmap(String projectId) =>
      _projectService.confirmMvpRoadmap(projectId);

  Future<Map<String, dynamic>> planMvpStage(String projectId, String stageId) =>
      _projectService.planMvpStage(projectId, stageId);

  Future<Map<String, dynamic>> activateMvpStage(
    String projectId,
    String stageId, {
    required List<Map<String, dynamic>> objectives,
    required List<String> weeklyFocus,
  }) =>
      _projectService.activateMvpStage(projectId, stageId, objectives: objectives, weeklyFocus: weeklyFocus);

  Future<StrategyListResult<Map<String, dynamic>>> generateStageServiceAssessment(
    String projectId,
    String stageId,
  ) =>
      _projectService.generateStageServiceAssessment(projectId, stageId);

  Future<StrategyListResult<Map<String, dynamic>>> confirmStageServiceAssessment(
    String projectId,
    String stageId,
    List<Map<String, dynamic>> decisions,
  ) =>
      _projectService.confirmStageServiceAssessment(projectId, stageId, decisions);

  Future<Map<String, dynamic>> previewStageRevision(
    String stageId, {
    String? hypothesis,
    List<String>? scope,
    List<String>? nonGoals,
    List<String>? exitCriteria,
  }) =>
      _projectService.previewStageRevision(
        stageId,
        hypothesis: hypothesis,
        scope: scope,
        nonGoals: nonGoals,
        exitCriteria: exitCriteria,
      );

  Future<Map<String, dynamic>> applyStageRevision(String stageId, String revisionId) =>
      _projectService.applyStageRevision(stageId, revisionId);

  Future<Map<String, dynamic>> generateWeek13(String stageId) =>
      _projectService.generateWeek13(stageId);

  Future<Map<String, dynamic>> confirmWeek13(String stageId, String decision, String rationale) =>
      _projectService.confirmWeek13(stageId, decision, rationale);

  // ====================================================================
  // Portfolios & Intelligence (delegated to PortfolioService)
  // ====================================================================

  Future<Map<String, dynamic>> detectPortfolioNecessity() =>
      _portfolioService.detectPortfolioNecessity();

  Future<StrategyListResult<Map<String, dynamic>>> getPortfolios() =>
      _portfolioService.getPortfolios();

  Future<Map<String, dynamic>> createPortfolio({
    required String name,
    String? description,
    String? strategicFocus,
  }) =>
      _portfolioService.createPortfolio(name: name, description: description, strategicFocus: strategicFocus);

  Future<StrategyListResult<Map<String, dynamic>>> getPortfolioProjects(String portfolioId) =>
      _portfolioService.getPortfolioProjects(portfolioId);

  Future<Map<String, dynamic>> addProjectToPortfolio(
    String portfolioId, {
    required String projectId,
    String strategicPriority = 'core',
    double capacityAllocation = 0.0,
    double founderAttentionHours = 0.0,
  }) =>
      _portfolioService.addProjectToPortfolio(
        portfolioId,
        projectId: projectId,
        strategicPriority: strategicPriority,
        capacityAllocation: capacityAllocation,
        founderAttentionHours: founderAttentionHours,
      );

  Future<Map<String, dynamic>> removeProjectFromPortfolio(String portfolioId, String projectId) =>
      _portfolioService.removeProjectFromPortfolio(portfolioId, projectId);

  Future<Map<String, dynamic>> getPortfolioImpactMatrix(String portfolioId) =>
      _portfolioService.getPortfolioImpactMatrix(portfolioId);

  Future<StrategyListResult<Map<String, dynamic>>> getPortfolioSwot(String portfolioId) =>
      _portfolioService.getPortfolioSwot(portfolioId);

  Future<Map<String, dynamic>> addPortfolioSwotItem(
    String portfolioId, {
    required String category,
    required String statement,
    String impact = 'medium',
    String likelihood = 'medium',
    String confidence = 'medium',
    String evidenceStatus = 'hypothesis',
  }) =>
      _portfolioService.addPortfolioSwotItem(
        portfolioId,
        category: category,
        statement: statement,
        impact: impact,
        likelihood: likelihood,
        confidence: confidence,
        evidenceStatus: evidenceStatus,
      );

  Future<StrategyListResult<Map<String, dynamic>>> getPortfolioTows(String portfolioId) =>
      _portfolioService.getPortfolioTows(portfolioId);

  Future<Map<String, dynamic>> addPortfolioTowsOption(
    String portfolioId, {
    required String quadrant,
    required String title,
    String tradeoffs = '',
    String expectedImpact = 'medium',
    String confidence = 'medium',
    String status = 'draft',
  }) =>
      _portfolioService.addPortfolioTowsOption(
        portfolioId,
        quadrant: quadrant,
        title: title,
        tradeoffs: tradeoffs,
        expectedImpact: expectedImpact,
        confidence: confidence,
        status: status,
      );

  Future<StrategyListResult<Map<String, dynamic>>> getPortfolioSynergies(String portfolioId) =>
      _portfolioService.getPortfolioSynergies(portfolioId);

  Future<Map<String, dynamic>> addPortfolioSynergy(
    String portfolioId, {
    required String sourceProjectId,
    required String targetProjectId,
    String synergyType = 'SHARED_CAPABILITY',
    required String description,
    double? estimatedValue,
    String status = 'identified',
  }) =>
      _portfolioService.addPortfolioSynergy(
        portfolioId,
        sourceProjectId: sourceProjectId,
        targetProjectId: targetProjectId,
        synergyType: synergyType,
        description: description,
        estimatedValue: estimatedValue,
        status: status,
      );

  Future<Map<String, dynamic>> deletePortfolioSynergy(String portfolioId, String synergyId) =>
      _portfolioService.deletePortfolioSynergy(portfolioId, synergyId);

  Future<StrategyListResult<Map<String, dynamic>>> getPortfolioDependencies(String portfolioId) =>
      _portfolioService.getPortfolioDependencies(portfolioId);

  Future<Map<String, dynamic>> addPortfolioDependency(
    String portfolioId, {
    required String predecessorProjectId,
    required String successorProjectId,
    String dependencyType = 'BLOCKS',
    String? description,
  }) =>
      _portfolioService.addPortfolioDependency(
        portfolioId,
        predecessorProjectId: predecessorProjectId,
        successorProjectId: successorProjectId,
        dependencyType: dependencyType,
        description: description,
      );

  Future<Map<String, dynamic>> deletePortfolioDependency(String portfolioId, String dependencyId) =>
      _portfolioService.deletePortfolioDependency(portfolioId, dependencyId);

  Future<StrategyListResult<Map<String, dynamic>>> getPortfolioOptions(String portfolioId) =>
      _portfolioService.getPortfolioOptions(portfolioId);

  Future<Map<String, dynamic>> createPortfolioOption(
    String portfolioId, {
    required String title,
    String? description,
    String? towsOptionId,
    double strategicFitScore = 0.8,
    double feasibilityScore = 0.7,
    String riskLevel = 'MEDIUM',
    String status = 'draft',
  }) =>
      _portfolioService.createPortfolioOption(
        portfolioId,
        title: title,
        description: description,
        towsOptionId: towsOptionId,
        strategicFitScore: strategicFitScore,
        feasibilityScore: feasibilityScore,
        riskLevel: riskLevel,
        status: status,
      );

  Future<Map<String, dynamic>> updatePortfolioOption(
    String portfolioId,
    String optionId, {
    String? status,
    double? strategicFitScore,
    double? feasibilityScore,
  }) =>
      _portfolioService.updatePortfolioOption(
        portfolioId,
        optionId,
        status: status,
        strategicFitScore: strategicFitScore,
        feasibilityScore: feasibilityScore,
      );

  Future<StrategyListResult<Map<String, dynamic>>> getPortfolioCycles(String portfolioId) =>
      _portfolioService.getPortfolioCycles(portfolioId);

  Future<Map<String, dynamic>> createPortfolioCycle(
    String portfolioId, {
    required String title,
    String? startDate,
    String? endDate,
  }) =>
      _portfolioService.createPortfolioCycle(
        portfolioId,
        title: title,
        startDate: startDate,
        endDate: endDate,
      );

  Future<Map<String, dynamic>> activatePortfolioCycle(String cycleId) =>
      _portfolioService.activatePortfolioCycle(cycleId);

  Future<Map<String, dynamic>> getCycleAllocations(String cycleId) =>
      _portfolioService.getCycleAllocations(cycleId);

  Future<Map<String, dynamic>> setCapacityAllocation(
    String cycleId, {
    required String projectId,
    required double allocatedPercentage,
  }) =>
      _portfolioService.setCapacityAllocation(
        cycleId,
        projectId: projectId,
        allocatedPercentage: allocatedPercentage,
      );

  Future<Map<String, dynamic>> setFounderAttentionAllocation(
    String cycleId, {
    required String projectId,
    required double allocatedHoursPerWeek,
  }) =>
      _portfolioService.setFounderAttentionAllocation(
        cycleId,
        projectId: projectId,
        allocatedHoursPerWeek: allocatedHoursPerWeek,
      );

  // ====================================================================
  // Founder & CEO Next Best Actions (delegated to FounderService)
  // ====================================================================

  Future<Map<String, dynamic>> getFounderProfile() => _founderService.getFounderProfile();

  Future<Map<String, dynamic>> updateFounderProfile({
    double? weeklyCapacityHours,
    int? maxActiveStrategicProjects,
  }) =>
      _founderService.updateFounderProfile(
        weeklyCapacityHours: weeklyCapacityHours,
        maxActiveStrategicProjects: maxActiveStrategicProjects,
      );

  Future<StrategyListResult<Map<String, dynamic>>> getCeoNextActions({int limit = 5}) =>
      _founderService.getCeoNextActions(limit: limit);

  Future<StrategyListResult<Map<String, dynamic>>> evaluateCeoNextActions({
    String? projectId,
    String? portfolioId,
  }) =>
      _founderService.evaluateCeoNextActions(projectId: projectId, portfolioId: portfolioId);

  Future<Map<String, dynamic>> updateNextActionStatus(String actionId, String status) =>
      _founderService.updateNextActionStatus(actionId, status);

  Future<StrategyListResult<Map<String, dynamic>>> getModelRunsAudit({int limit = 20}) =>
      _founderService.getModelRunsAudit(limit: limit);

  Future<StrategyListResult<Map<String, dynamic>>> getModelProfiles() =>
      _founderService.getModelProfiles();

  Future<Map<String, dynamic>> updateModelProfile(
    String profileId, {
    String? displayName,
    double? temperature,
    bool? isActive,
  }) =>
      _founderService.updateModelProfile(
        profileId,
        displayName: displayName,
        temperature: temperature,
        isActive: isActive,
      );
}
