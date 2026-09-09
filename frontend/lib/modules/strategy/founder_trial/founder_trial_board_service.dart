import 'package:http/http.dart' as http;

import '../../../core/network/api_result.dart';
import '../../../core/network/mvp_endpoints.g.dart';
import '../../../core/network/mvp_request_client.dart';
import 'founder_trial_board_models.dart';

/// Đọc Founder Trial Board và tạo experiment theo hợp đồng nghiêm ngặt của
/// luồng Founder Trial (bắt buộc assumption + method + success criteria).
class FounderTrialBoardService {
  FounderTrialBoardService({MvpRequestClient? client, http.Client? httpClient})
      : _client = client ?? MvpRequestClient(httpClient: httpClient);

  final MvpRequestClient _client;

  Future<ApiResult<FounderTrialBoard>> fetch(String projectId) {
    return _client.request<FounderTrialBoard>(
      MvpEndpoint.strategyFounderTrialBoardRead,
      pathParams: {'projectId': projectId},
      decode: (json) => FounderTrialBoard.fromJson(json as Map<String, dynamic>),
    );
  }

  Future<ApiResult<FounderTrialExperiment>> createExperiment({
    required String projectId,
    required String assumptionId,
    required String hypothesis,
    required String method,
    required String successCriteria,
  }) {
    return _client.request<FounderTrialExperiment>(
      MvpEndpoint.strategyFounderTrialExperimentCreate,
      pathParams: {'projectId': projectId},
      body: {
        'assumptionId': assumptionId,
        'hypothesis': hypothesis,
        'method': method,
        'successCriteria': successCriteria,
      },
      decode: (json) => FounderTrialExperiment.fromJson(json as Map<String, dynamic>),
    );
  }
}
