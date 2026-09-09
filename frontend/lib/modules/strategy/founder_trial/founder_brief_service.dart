import 'package:http/http.dart' as http;

import '../../../core/network/api_result.dart';
import '../../../core/network/mvp_endpoints.g.dart';
import '../../../core/network/mvp_request_client.dart';
import 'founder_brief_models.dart';

class FounderBriefService {
  FounderBriefService({MvpRequestClient? client, http.Client? httpClient})
      : _client = client ?? MvpRequestClient(httpClient: httpClient);

  final MvpRequestClient _client;

  Future<ApiResult<FounderBrief>> fetch(String projectId) {
    return _client.request<FounderBrief>(
      MvpEndpoint.strategyFounderBriefRead,
      pathParams: {'projectId': projectId},
      decode: (json) => FounderBrief.fromJson(json as Map<String, dynamic>),
    );
  }
}
