// Service gọi endpoint Task 5 (POST /operations/objectives/:id/generate-weekly-cycle)
// để sinh N weekly_plans rỗng từ 1 Objective đã publish. Dùng chung
// StrategyServiceBase như okr_service.dart — ApiClient tự gắn header
// X-Workspace-Id, không cần query workspace_id thủ công.
import '../../../core/network/api_client.dart';
import 'strategy_service_base.dart';

class OkrWeeklyGeneratorService extends StrategyServiceBase {
  Future<Map<String, dynamic>> generate(String objectiveId, int durationWeeks) async {
    if (durationWeeks < 1 || durationWeeks > 12) {
      throw ArgumentError('durationWeeks must be between 1 and 12');
    }
    await requireWorkspaceId();
    final response = await ApiClient.post(
      '/operations/objectives/$objectiveId/generate-weekly-cycle',
      body: {'durationWeeks': durationWeeks},
    );
    return decode(response) as Map<String, dynamic>;
  }
}
