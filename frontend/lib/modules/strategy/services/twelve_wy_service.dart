import '../../../core/network/api_result.dart';
import '../../../data/models/twelve_wy_model.dart';
import 'strategy_mvp_client.dart';
import '../models/mvp_strategy_models.dart';

class TwelveWyService {
  final StrategyMvpClient _client;

  TwelveWyService({StrategyMvpClient? client}) : _client = client ?? StrategyMvpClient();

  Future<ApiResult<List<MvpTwelveWeekCycle>>> listCyclesResult() async {
    return _client.listTwelveWeekCycles();
  }

  Future<List<TwelveWeekCycleModel>> getCycles() async {
    final res = await _client.listTwelveWeekCycles();
    if (res is ApiSuccess<List<MvpTwelveWeekCycle>>) {
      return res.data.map((c) => TwelveWeekCycleModel(
        id: int.tryParse(c.id) ?? 0,
        workspaceId: int.tryParse(c.workspaceId) ?? 0,
        projectId: c.projectId != null ? int.tryParse(c.projectId!) : null,
        title: c.theme ?? 'Chu Kỳ 12 Tuần',
        visionStatement: c.visionStatement,
        stageAtStart: c.stageAtStart,
        currentWeek: c.currentWeek,
        totalWeeks: c.durationWeeks,
        overallExecutionScore: c.overallExecutionScore,
        status: c.status,
        createdAt: DateTime.tryParse(c.createdAt) ?? DateTime.now(),
      )).toList();
    }
    return [];
  }

  Future<TwelveWyDashboardModel?> getDashboard(dynamic projectId) async {
    final cycles = await getCycles();
    if (cycles.isNotEmpty) {
      final activeCycle = cycles.first;
      return TwelveWyDashboardModel(
        cycle: activeCycle,
        currentWeek: activeCycle.currentWeek,
        currentWeekExecutionScore: activeCycle.overallExecutionScore,
        tacticsByWeek: {},
        weeklyScores: {},
      );
    }
    return null;
  }

  Future<TwelveWeekCycleModel?> createOrGetCycle(
    dynamic projectId, {
    String? title,
    String? visionStatement,
  }) async {
    final cycles = await getCycles();
    if (cycles.isNotEmpty) return cycles.first;
    return null;
  }

  Future<TacticalItemModel?> createTactic({
    required dynamic projectId,
    dynamic cycleId,
    required int weekNumber,
    required String title,
    String description = '',
    dynamic towsOptionId,
    dynamic hypothesisId,
    required String leadIndicatorName,
    int targetCount = 1,
    int actualCount = 0,
    String status = 'PLANNED',
    String ownerRole = 'Founder',
  }) async {
    return TacticalItemModel(
      id: DateTime.now().millisecondsSinceEpoch,
      workspaceId: 0,
      projectId: int.tryParse(projectId?.toString() ?? '') ?? 0,
      cycleId: int.tryParse(cycleId?.toString() ?? '') ?? 0,
      weekNumber: weekNumber,
      title: title,
      description: description,
      leadIndicatorName: leadIndicatorName,
      targetCount: targetCount,
      actualCount: actualCount,
      status: status,
      ownerRole: ownerRole,
      createdAt: DateTime.now(),
    );
  }

  Future<TacticalItemModel?> updateTactic({
    required int tacticId,
    int? actualCount,
    String? status,
    String? title,
    String? description,
  }) async {
    return null;
  }

  Future<WeeklyReviewModel?> generateWeeklyReview({
    required int cycleId,
    required int weekNumber,
  }) async {
    return null;
  }

  Future<ApiResult<List<MvpWeeklyPlan>>> getWeeklyPlans() async {
    return _client.listTwelveWeekPlans();
  }

  Future<ApiResult<List<MvpWeeklyCommitment>>> getWeeklyCommitments() async {
    return _client.listTwelveWeekCommitments();
  }
}
