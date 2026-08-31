import '../../../core/network/api_result.dart';
import 'strategy_mvp_client.dart';
import '../models/mvp_strategy_models.dart';

class OkrService {
  final StrategyMvpClient _client;

  OkrService({StrategyMvpClient? client}) : _client = client ?? StrategyMvpClient();

  Future<ApiResult<List<MvpOkrCycle>>> getCycles() async {
    return _client.listOkrCycles();
  }

  Future<ApiResult<List<MvpObjective>>> getObjectives() async {
    return _client.listObjectives();
  }

  Future<ApiResult<void>> deleteObjective(String objectiveId) async {
    return _client.deleteObjective(objectiveId);
  }

  Future<ApiResult<MvpObjectiveProgress>> getObjectiveProgress(String objectiveId) async {
    return _client.getObjectiveProgress(objectiveId);
  }
}
