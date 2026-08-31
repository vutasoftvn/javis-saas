import '../../../core/network/api_client.dart';
import '../models/strategy_list_result.dart';
import 'strategy_service_base.dart';

/// OKRs & Key Results
class OkrService extends StrategyServiceBase {
  Future<StrategyListResult<Map<String, dynamic>>> getOkrCycles() async {
    final workspaceId = await getWorkspaceId();
    if (workspaceId == null) {
      return const StrategyListResult.failure('Chưa xác định workspace hiện tại');
    }
    try {
      final response = await ApiClient.get('/okrs/cycles?workspace_id=$workspaceId');
      return decodeList(response, 'cycles');
    } catch (e) {
      return StrategyListResult.failure(e.toString());
    }
  }

  Future<Map<String, dynamic>> createOkrCycle({
    required String name,
    DateTime? startDate,
    DateTime? endDate,
    String? status,
  }) async {
    final workspaceId = await requireWorkspaceId();
    final response = await ApiClient.post(
      '/okrs/cycles?workspace_id=$workspaceId',
      body: {
        'name': name,
        'start_date': ?startDate?.toIso8601String(),
        'end_date': ?endDate?.toIso8601String(),
        'status': ?status,
      },
    );
    return decode(response);
  }

  Future<StrategyListResult<Map<String, dynamic>>> getObjectives({String? cycleId}) async {
    final workspaceId = await getWorkspaceId();
    if (workspaceId == null) {
      return const StrategyListResult.failure('Chưa xác định workspace hiện tại');
    }
    final query = cycleId != null ? 'workspace_id=$workspaceId&cycle_id=$cycleId' : 'workspace_id=$workspaceId';
    try {
      final response = await ApiClient.get('/okrs/objectives?$query');
      return decodeList(response, 'objectives');
    } catch (e) {
      return StrategyListResult.failure(e.toString());
    }
  }

  Future<Map<String, dynamic>> createObjective({
    required String title,
    String? cycleId,
    String? status,
  }) async {
    final workspaceId = await requireWorkspaceId();
    final response = await ApiClient.post(
      '/okrs/objectives?workspace_id=$workspaceId',
      body: {
        'title': title,
        if (cycleId != null && cycleId.isNotEmpty) 'cycle_id': cycleId,
        if (status != null && status.isNotEmpty) 'status': status,
      },
    );
    return decode(response);
  }

  Future<Map<String, dynamic>> updateObjective(
    String objectiveId, {
    String? title,
    String? status,
  }) async {
    final workspaceId = await requireWorkspaceId();
    final response = await ApiClient.put(
      '/okrs/objectives/$objectiveId?workspace_id=$workspaceId',
      body: {
        'title': ?title,
        'status': ?status,
      },
    );
    return decode(response);
  }

  Future<void> deleteObjective(String objectiveId) async {
    final workspaceId = await requireWorkspaceId();
    final response = await ApiClient.delete('/okrs/objectives/$objectiveId?workspace_id=$workspaceId');
    decode(response);
  }

  Future<StrategyListResult<Map<String, dynamic>>> getKeyResults({String? objectiveId}) async {
    final workspaceId = await getWorkspaceId();
    if (workspaceId == null) {
      return const StrategyListResult.failure('Chưa xác định workspace hiện tại');
    }
    final query = objectiveId != null ? 'workspace_id=$workspaceId&objective_id=$objectiveId' : 'workspace_id=$workspaceId';
    try {
      final response = await ApiClient.get('/okrs/key-results?$query');
      return decodeList(response, 'key_results');
    } catch (e) {
      return StrategyListResult.failure(e.toString());
    }
  }

  Future<Map<String, dynamic>> createKeyResult({
    required String objectiveId,
    String? title,
    double? baselineValue,
    double? currentValue,
    double? targetValue,
    String? unit,
    String? cadence,
    String? status,
  }) async {
    final workspaceId = await requireWorkspaceId();
    final response = await ApiClient.post(
      '/okrs/key-results?workspace_id=$workspaceId',
      body: {
        'objective_id': objectiveId,
        if (title != null && title.isNotEmpty) 'title': title,
        'baseline_value': baselineValue ?? 0.0,
        'current_value': currentValue ?? 0.0,
        'target_value': targetValue ?? 100.0,
        'unit': unit ?? '%',
        'cadence': cadence ?? 'weekly',
        'status': status ?? 'active',
      },
    );
    return decode(response);
  }

  Future<Map<String, dynamic>> updateKeyResult(
    String keyResultId, {
    double? currentValue,
    double? targetValue,
    String? unit,
    String? status,
  }) async {
    final workspaceId = await requireWorkspaceId();
    final response = await ApiClient.put(
      '/okrs/key-results/$keyResultId?workspace_id=$workspaceId',
      body: {
        'current_value': ?currentValue,
        'target_value': ?targetValue,
        'unit': ?unit,
        'status': ?status,
      },
    );
    return decode(response);
  }

  Future<void> deleteKeyResult(String keyResultId) async {
    final workspaceId = await requireWorkspaceId();
    final response = await ApiClient.delete('/okrs/key-results/$keyResultId?workspace_id=$workspaceId');
    decode(response);
  }

  Future<Map<String, dynamic>> generateAiOkrs({
    String? towsId,
    int objectivesCount = 2,
    int krsPerObjectiveCount = 3,
    String? cycleId,
  }) async {
    final workspaceId = await requireWorkspaceId();
    final body = <String, dynamic>{
      'objectives_count': objectivesCount,
      'krs_per_objective_count': krsPerObjectiveCount,
    };
    if (towsId != null && towsId.isNotEmpty) {
      body['tows_id'] = towsId;
    }
    if (cycleId != null && cycleId.isNotEmpty) {
      body['cycle_id'] = cycleId;
    }

    final response = await ApiClient.post(
      '/okrs/generate-ai?workspace_id=$workspaceId',
      body: body,
    );
    return decode(response);
  }
}
