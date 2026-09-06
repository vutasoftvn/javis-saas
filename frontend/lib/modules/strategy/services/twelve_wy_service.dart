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

  // IA05 — trước đây hàm này trả về 1 TacticalItemModel dựng tại client
  // (id = timestamp), KHÔNG hề gọi backend: UI báo "Đã thêm Tactic mới"
  // thành công nhưng dữ liệu chỉ tồn tại trong bộ nhớ của lần build hiện
  // tại — reload (kể cả gọi lại getDashboard() ngay sau đó, vốn luôn trả
  // tacticsByWeek rỗng) là mất trắng. Backend hiện KHÔNG có khái niệm
  // "tactic" (towsOptionId/leadIndicatorName/targetCount...) — đây là tính
  // năng F11 chưa xây, không phải lỗi wiring đơn giản. Throw rõ ràng
  // (cùng pattern đã dùng ở FinanceTT58Service cho tính năng chưa khả dụng)
  // để caller BẮT BUỘC xử lý thất bại thay vì âm thầm coi là đã lưu.
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
    throw UnimplementedError(
      'Tính năng Tactic (12-Tuần) chưa có backend lưu trữ — chưa thể tạo/lưu tactic.',
    );
  }

  Future<TacticalItemModel?> updateTactic({
    required int tacticId,
    int? actualCount,
    String? status,
    String? title,
    String? description,
  }) async {
    throw UnimplementedError(
      'Tính năng Tactic (12-Tuần) chưa có backend lưu trữ — chưa thể cập nhật tactic.',
    );
  }

  Future<WeeklyReviewModel?> generateWeeklyReview({
    required int cycleId,
    required int weekNumber,
  }) async {
    throw UnimplementedError(
      'Tính năng Weekly Review (12-Tuần) chưa có backend lưu trữ — chưa thể tạo weekly review.',
    );
  }

  Future<ApiResult<List<MvpWeeklyPlan>>> getWeeklyPlans() async {
    return _client.listTwelveWeekPlans();
  }

  Future<ApiResult<List<MvpWeeklyCommitment>>> getWeeklyCommitments() async {
    return _client.listTwelveWeekCommitments();
  }

  Future<ApiResult<MvpWeeklyPlan>> updateWeeklyPlan({
    required String id,
    double? executionScore,
    double? outcomeScore,
    String? reflection,
  }) async {
    return _client.updateWeeklyPlan(
      id: id,
      executionScore: executionScore,
      outcomeScore: outcomeScore,
      reflection: reflection,
    );
  }

  Future<ApiResult<MvpExecutionCycleView>> getExecutionCycleView({
    required String projectId,
    String? cycleId,
  }) async {
    return _client.getExecutionCycleView(
      projectId: projectId,
      cycleId: cycleId,
    );
  }
}
