import '../../../core/network/api_client.dart';
import '../models/strategy_list_result.dart';
import 'strategy_service_base.dart';

/// 12-Week Execution Plans, Milestones, Gate Decisions & Weekly Reviews
class TwelveWeekService extends StrategyServiceBase {
  // ====================================================================
  // 12-Week Execution Plans & Commitments
  // ====================================================================

  Future<StrategyListResult<Map<String, dynamic>>> getTwelveWeekCycles() async {
    final workspaceId = await getWorkspaceId();
    if (workspaceId == null) {
      return const StrategyListResult.failure('Chưa xác định workspace hiện tại');
    }
    try {
      final response = await ApiClient.get('/execution/twelve-week-cycles?workspace_id=$workspaceId');
      return decodeList(response, 'cycles');
    } catch (e) {
      return StrategyListResult.failure(e.toString());
    }
  }

  Future<Map<String, dynamic>> createTwelveWeekCycle({
    required String theme,
    String? projectId,
    int? durationWeeks,
    DateTime? startDate,
    DateTime? endDate,
  }) async {
    final workspaceId = await requireWorkspaceId();
    final response = await ApiClient.post(
      '/execution/twelve-week-cycles?workspace_id=$workspaceId',
      body: {
        'theme': theme,
        'project_id': projectId != null ? int.tryParse(projectId) : null,
        'duration_weeks': durationWeeks ?? 13,
        'start_date': ?startDate?.toIso8601String(),
        'end_date': ?endDate?.toIso8601String(),
      },
    );
    return decode(response);
  }

  Future<Map<String, dynamic>> getCycleTimeline(String cycleId) async {
    final workspaceId = await requireWorkspaceId();
    try {
      final response = await ApiClient.get(
        '/execution/twelve-week-cycles/$cycleId/timeline?workspace_id=$workspaceId',
      );
      return decode(response);
    } catch (_) {
      return {};
    }
  }

  Future<StrategyListResult<Map<String, dynamic>>> getWeeklyPlans({String? cycleId}) async {
    final workspaceId = await getWorkspaceId();
    if (workspaceId == null) {
      return const StrategyListResult.failure('Chưa xác định workspace hiện tại');
    }
    final query = cycleId != null ? 'workspace_id=$workspaceId&cycle_id=$cycleId' : 'workspace_id=$workspaceId';
    try {
      final response = await ApiClient.get('/execution/weekly-plans?$query');
      return decodeList(response, 'plans');
    } catch (e) {
      return StrategyListResult.failure(e.toString());
    }
  }

  Future<Map<String, dynamic>> createWeeklyPlan({
    required int weekNo,
    String? cycleId,
    String? focus,
    DateTime? startDate,
    DateTime? endDate,
  }) async {
    final workspaceId = await requireWorkspaceId();
    final response = await ApiClient.post(
      '/execution/weekly-plans?workspace_id=$workspaceId',
      body: {
        'week_no': weekNo,
        'cycle_id': ?cycleId,
        'focus': ?focus,
        'start_date': ?startDate?.toIso8601String(),
        'end_date': ?endDate?.toIso8601String(),
      },
    );
    return decode(response);
  }

  Future<Map<String, dynamic>> updateWeeklyPlan(
    String planId, {
    String? focus,
    double? executionScore,
    String? reflection,
    DateTime? startDate,
    DateTime? endDate,
  }) async {
    final workspaceId = await requireWorkspaceId();
    final response = await ApiClient.put(
      '/execution/weekly-plans/$planId?workspace_id=$workspaceId',
      body: {
        'focus': ?focus,
        'execution_score': ?executionScore,
        'reflection': ?reflection,
        'start_date': ?startDate?.toIso8601String(),
        'end_date': ?endDate?.toIso8601String(),
      },
    );
    return decode(response);
  }

  Future<StrategyListResult<Map<String, dynamic>>> getWeeklyCommitments({String? weeklyPlanId}) async {
    final workspaceId = await getWorkspaceId();
    if (workspaceId == null) {
      return const StrategyListResult.failure('Chưa xác định workspace hiện tại');
    }
    final query = weeklyPlanId != null ? 'workspace_id=$workspaceId&weekly_plan_id=$weeklyPlanId' : 'workspace_id=$workspaceId';
    try {
      final response = await ApiClient.get('/execution/weekly-commitments?$query');
      return decodeList(response, 'commitments');
    } catch (e) {
      return StrategyListResult.failure(e.toString());
    }
  }

  Future<Map<String, dynamic>> createWeeklyCommitment({
    required String weeklyPlanId,
    required String title,
    String? plannedEffort,
    String? status,
  }) async {
    final workspaceId = await requireWorkspaceId();
    final response = await ApiClient.post(
      '/execution/weekly-commitments?workspace_id=$workspaceId',
      body: {
        'weekly_plan_id': weeklyPlanId,
        'title': title,
        'planned_effort': plannedEffort ?? 'medium',
        'status': status ?? 'todo',
      },
    );
    return decode(response);
  }

  Future<Map<String, dynamic>> updateWeeklyCommitment(
    String commitmentId, {
    String? title,
    String? status,
    String? plannedEffort,
  }) async {
    final workspaceId = await requireWorkspaceId();
    final response = await ApiClient.put(
      '/execution/weekly-commitments/$commitmentId?workspace_id=$workspaceId',
      body: {
        'title': ?title,
        'status': ?status,
        'planned_effort': ?plannedEffort,
      },
    );
    return decode(response);
  }

  Future<void> deleteWeeklyCommitment(String commitmentId) async {
    final workspaceId = await requireWorkspaceId();
    final response = await ApiClient.delete('/execution/weekly-commitments/$commitmentId?workspace_id=$workspaceId');
    decode(response);
  }

  // ====================================================================
  // mCOSA V12 13-Week Execution Engine & Stage-Gate Governance (Sprint 3)
  // ====================================================================

  Future<StrategyListResult<Map<String, dynamic>>> getCycleStages(String cycleId) async {
    final workspaceId = await getWorkspaceId();
    if (workspaceId == null) {
      return const StrategyListResult.failure('Chưa xác định workspace hiện tại');
    }
    try {
      final response = await ApiClient.get('/execution/twelve-week-cycles/$cycleId/stages?workspace_id=$workspaceId');
      return decodeList(response, 'stages');
    } catch (e) {
      return StrategyListResult.failure(e.toString());
    }
  }

  Future<StrategyListResult<Map<String, dynamic>>> generateStandardCycleStages(String cycleId) async {
    final workspaceId = await requireWorkspaceId();
    try {
      final response = await ApiClient.post(
        '/execution/twelve-week-cycles/$cycleId/stages/generate-standard?workspace_id=$workspaceId',
      );
      return decodeList(response, 'stages');
    } catch (e) {
      return StrategyListResult.failure(e.toString());
    }
  }

  Future<Map<String, dynamic>> createCycleStage(
    String cycleId, {
    required String name,
    required int startWeek,
    required int endWeek,
    required int orderNo,
    String? purpose,
    Map<String, dynamic>? expectedOutcomes,
  }) async {
    final workspaceId = await requireWorkspaceId();
    final response = await ApiClient.post(
      '/execution/twelve-week-cycles/$cycleId/stages?workspace_id=$workspaceId',
      body: {
        'name': name,
        'start_week': startWeek,
        'end_week': endWeek,
        'order_no': orderNo,
        'purpose': ?purpose,
        'expected_outcomes': ?expectedOutcomes,
      },
    );
    return decode(response);
  }

  Future<Map<String, dynamic>> updateCycleStage(
    String stageId, {
    String? name,
    String? purpose,
    int? startWeek,
    int? endWeek,
    String? status,
    Map<String, dynamic>? expectedOutcomes,
  }) async {
    final workspaceId = await requireWorkspaceId();
    final response = await ApiClient.put(
      '/execution/stages/$stageId?workspace_id=$workspaceId',
      body: {
        'name': ?name,
        'purpose': ?purpose,
        'start_week': ?startWeek,
        'end_week': ?endWeek,
        'status': ?status,
        'expected_outcomes': ?expectedOutcomes,
      },
    );
    return decode(response);
  }

  Future<void> deleteCycleStage(String stageId) async {
    final workspaceId = await requireWorkspaceId();
    final response = await ApiClient.delete('/execution/stages/$stageId?workspace_id=$workspaceId');
    decode(response);
  }

  Future<StrategyListResult<Map<String, dynamic>>> getMilestones({String? cycleId, String? stageId, String? projectId}) async {
    final workspaceId = await getWorkspaceId();
    if (workspaceId == null) {
      return const StrategyListResult.failure('Chưa xác định workspace hiện tại');
    }
    final params = <String>['workspace_id=$workspaceId'];
    if (cycleId != null) params.add('cycle_id=$cycleId');
    if (stageId != null) params.add('stage_id=$stageId');
    if (projectId != null) params.add('project_id=$projectId');
    try {
      final response = await ApiClient.get('/execution/milestones?${params.join('&')}');
      return decodeList(response, 'milestones');
    } catch (e) {
      return StrategyListResult.failure(e.toString());
    }
  }

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
  }) async {
    final workspaceId = await requireWorkspaceId();
    final response = await ApiClient.post(
      '/execution/milestones?workspace_id=$workspaceId',
      body: {
        'name': name,
        'cycle_id': ?cycleId,
        'stage_id': ?stageId,
        'project_id': ?projectId,
        'description': ?description,
        'due_week': ?dueWeek,
        'acceptance_criteria': ?acceptanceCriteria,
        'required_artifacts': ?requiredArtifacts,
        'required_metrics': ?requiredMetrics,
      },
    );
    return decode(response);
  }

  Future<Map<String, dynamic>> updateMilestone(
    String milestoneId, {
    String? name,
    String? description,
    int? dueWeek,
    String? status,
    String? acceptanceCriteria,
  }) async {
    final workspaceId = await requireWorkspaceId();
    final response = await ApiClient.put(
      '/execution/milestones/$milestoneId?workspace_id=$workspaceId',
      body: {
        'name': ?name,
        'description': ?description,
        'due_week': ?dueWeek,
        'status': ?status,
        'acceptance_criteria': ?acceptanceCriteria,
      },
    );
    return decode(response);
  }

  Future<void> deleteMilestone(String milestoneId) async {
    final workspaceId = await requireWorkspaceId();
    final response = await ApiClient.delete('/execution/milestones/$milestoneId?workspace_id=$workspaceId');
    decode(response);
  }

  Future<Map<String, dynamic>> linkMilestoneEvidence(
    String milestoneId,
    String evidenceId, {
    String? relevanceNote,
  }) async {
    final workspaceId = await requireWorkspaceId();
    final response = await ApiClient.post(
      '/execution/milestones/$milestoneId/evidence?workspace_id=$workspaceId',
      body: {
        'evidence_id': evidenceId,
        'relevance_note': ?relevanceNote,
      },
    );
    return decode(response);
  }

  Future<void> unlinkMilestoneEvidence(String milestoneId, String evidenceId) async {
    final workspaceId = await requireWorkspaceId();
    final response = await ApiClient.delete(
      '/execution/milestones/$milestoneId/evidence/$evidenceId?workspace_id=$workspaceId',
    );
    decode(response);
  }

  Future<StrategyListResult<Map<String, dynamic>>> getGateDecisions({String? projectId, String? stageId, String? milestoneId}) async {
    final workspaceId = await getWorkspaceId();
    if (workspaceId == null) {
      return const StrategyListResult.failure('Chưa xác định workspace hiện tại');
    }
    final params = <String>['workspace_id=$workspaceId'];
    if (projectId != null) params.add('project_id=$projectId');
    if (stageId != null) params.add('stage_id=$stageId');
    if (milestoneId != null) params.add('milestone_id=$milestoneId');
    try {
      final response = await ApiClient.get('/execution/gate-decisions?${params.join('&')}');
      return decodeList(response, 'gate_decisions');
    } catch (e) {
      return StrategyListResult.failure(e.toString());
    }
  }

  Future<Map<String, dynamic>> recordGateDecision({
    required String projectId,
    required String decision,
    required String rationale,
    String? milestoneId,
    String? stageId,
    String? evidenceSummary,
    String? nextStepInstructions,
  }) async {
    final workspaceId = await requireWorkspaceId();
    final response = await ApiClient.post(
      '/execution/gate-decisions?workspace_id=$workspaceId',
      body: {
        'project_id': projectId,
        'decision': decision,
        'rationale': rationale,
        'milestone_id': ?milestoneId,
        'stage_id': ?stageId,
        'evidence_summary': ?evidenceSummary,
        'next_step_instructions': ?nextStepInstructions,
      },
    );
    return decode(response);
  }

  Future<Map<String, dynamic>?> getCycleContract(String cycleId) async {
    final workspaceId = await requireWorkspaceId();
    try {
      final response = await ApiClient.get(
        '/execution/twelve-week-cycles/$cycleId/contract?workspace_id=$workspaceId',
      );
      return decode(response);
    } catch (_) {
      return null;
    }
  }

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
  }) async {
    final workspaceId = await requireWorkspaceId();
    final response = await ApiClient.post(
      '/execution/twelve-week-cycles/$cycleId/contract?workspace_id=$workspaceId',
      body: {
        'success_definition': successDefinition,
        'founder_capacity_per_week': ?founderCapacityPerWeek,
        'reserved_buffer_percent': ?reservedBufferPercent,
        'ai_budget': ?aiBudget,
        'operating_budget': ?operatingBudget,
        'goal_ids': ?goalIds,
        'kr_ids': ?krIds,
        'status': ?status,
      },
    );
    return decode(response);
  }

  Future<Map<String, dynamic>> updateWeeklyMission(
    String planId, {
    String? mission,
    Map<String, dynamic>? successCriteria,
    String? stageId,
    double? outcomeScore,
  }) async {
    final workspaceId = await requireWorkspaceId();
    final response = await ApiClient.put(
      '/execution/weekly-plans/$planId/mission?workspace_id=$workspaceId',
      body: {
        'mission': ?mission,
        'success_criteria': ?successCriteria,
        'stage_id': ?stageId,
        'outcome_score': ?outcomeScore,
      },
    );
    return decode(response);
  }

  // ====================================================================
  // mCOSA V12 Planning Compiler → V10 Runtime (Sprint 4)
  // ====================================================================

  Future<Map<String, dynamic>> compileCycle(String cycleId) async {
    final workspaceId = await requireWorkspaceId();
    final response = await ApiClient.post(
      '/execution/twelve-week-cycles/$cycleId/compile?workspace_id=$workspaceId',
    );
    return decode(response);
  }

  Future<Map<String, dynamic>> compileWeeklyPlan(String planId) async {
    final workspaceId = await requireWorkspaceId();
    final response = await ApiClient.post(
      '/execution/weekly-plans/$planId/compile?workspace_id=$workspaceId',
    );
    return decode(response);
  }

  Future<Map<String, dynamic>> getCycleCompilationStatus(String cycleId) async {
    final workspaceId = await requireWorkspaceId();
    final response = await ApiClient.get(
      '/execution/twelve-week-cycles/$cycleId/compilation-status?workspace_id=$workspaceId',
    );
    return decode(response);
  }

  // ====================================================================
  // mCOSA V12 Weekly Review & Week 13 Strategic Transition (Sprint 5)
  // ====================================================================

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
  }) async {
    final workspaceId = await requireWorkspaceId();
    final response = await ApiClient.post(
      '/execution/twelve-week-cycles/$cycleId/weekly-reviews?workspace_id=$workspaceId',
      body: {
        'weekly_plan_id': weeklyPlanId,
        'execution_score': executionScore,
        'outcome_score': outcomeScore,
        'evidence_learned': ?evidenceLearned,
        'assumptions_confirmed': ?assumptionsConfirmed,
        'assumptions_invalidated': ?assumptionsInvalidated,
        'recommendation': ?recommendation,
        'narrative_summary': ?narrativeSummary,
      },
    );
    return decode(response);
  }

  Future<StrategyListResult<Map<String, dynamic>>> getWeeklyReviews(String cycleId) async {
    final workspaceId = await getWorkspaceId();
    if (workspaceId == null) {
      return const StrategyListResult.failure('Chưa xác định workspace hiện tại');
    }
    try {
      final response = await ApiClient.get(
        '/execution/twelve-week-cycles/$cycleId/weekly-reviews?workspace_id=$workspaceId',
      );
      return decodeList(response, 'weekly_reviews');
    } catch (e) {
      return StrategyListResult.failure(e.toString());
    }
  }

  Future<Map<String, dynamic>?> getWeeklyPlanReview(String planId) async {
    final workspaceId = await requireWorkspaceId();
    try {
      final response = await ApiClient.get(
        '/execution/weekly-plans/$planId/review?workspace_id=$workspaceId',
      );
      return decode(response);
    } catch (_) {
      return null;
    }
  }

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
  }) async {
    final workspaceId = await requireWorkspaceId();
    final response = await ApiClient.post(
      '/execution/twelve-week-cycles/$cycleId/week13/finalize?workspace_id=$workspaceId',
      body: {
        'overall_execution_score': overallExecutionScore,
        'overall_outcome_score': overallOutcomeScore,
        'okr_achievement_rate': okrAchievementRate,
        'strategic_learnings': ?strategicLearnings,
        'systemic_blockers': ?systemicBlockers,
        'portfolio_adjustments': ?portfolioAdjustments,
        'next_cycle_recommendations': ?nextCycleRecommendations,
        'celebration_title': ?celebrationTitle,
        'milestones_achieved': ?milestonesAchieved,
        'top_performers_recognized': ?topPerformersRecognized,
        'rewards_or_rituals': ?rewardsOrRituals,
        'reflection_notes': ?reflectionNotes,
      },
    );
    return decode(response);
  }

  Future<Map<String, dynamic>?> getWeek13Review(String cycleId) async {
    final workspaceId = await requireWorkspaceId();
    try {
      final response = await ApiClient.get(
        '/execution/twelve-week-cycles/$cycleId/week13/review?workspace_id=$workspaceId',
      );
      return decode(response);
    } catch (_) {
      return null;
    }
  }

  Future<Map<String, dynamic>?> getWeek13Celebration(String cycleId) async {
    final workspaceId = await requireWorkspaceId();
    try {
      final response = await ApiClient.get(
        '/execution/twelve-week-cycles/$cycleId/week13/celebration?workspace_id=$workspaceId',
      );
      return decode(response);
    } catch (_) {
      return null;
    }
  }

  Future<Map<String, dynamic>> getWeek13Readiness(String cycleId) async {
    final workspaceId = await requireWorkspaceId();
    final response = await ApiClient.get(
      '/execution/twelve-week-cycles/$cycleId/week13/readiness?workspace_id=$workspaceId',
    );
    return decode(response);
  }
}
