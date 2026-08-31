import 'package:http/http.dart' as http;
import '../../../core/network/api_result.dart';
import '../../../core/network/mvp_endpoints.g.dart';
import '../../../core/network/mvp_request_client.dart';
import '../models/mvp_runtime_models.dart';

class WorkspaceRuntimeMvpClient {
  final MvpRequestClient _client;

  WorkspaceRuntimeMvpClient({MvpRequestClient? client, http.Client? httpClient})
      : _client = client ?? MvpRequestClient(httpClient: httpClient);

  Future<ApiResult<List<MvpRuntimeItem>>> listNeedsYou() async {
    return _client.request<List<MvpRuntimeItem>>(
      MvpEndpoint.workspaceRuntimeNeedsYou,
      decode: (json) {
        final list = json is List ? json : (json as Map<String, dynamic>)['items'] as List? ?? [];
        return list
            .whereType<Map<String, dynamic>>()
            .map((e) => MvpRuntimeItem.fromJson(e))
            .toList();
      },
    );
  }

  Future<ApiResult<List<MvpRuntimeItem>>> listBlockers() async {
    return _client.request<List<MvpRuntimeItem>>(
      MvpEndpoint.workspaceRuntimeBlockers,
      decode: (json) {
        final list = json is List ? json : (json as Map<String, dynamic>)['items'] as List? ?? [];
        return list
            .whereType<Map<String, dynamic>>()
            .map((e) => MvpRuntimeItem.fromJson(e))
            .toList();
      },
    );
  }

  Future<ApiResult<MvpRuntimeItemDetail>> getItem({
    required String sourceKind,
    required String sourceId,
  }) async {
    return _client.request<MvpRuntimeItemDetail>(
      MvpEndpoint.workspaceRuntimeItemGet,
      pathParams: {
        'sourceKind': sourceKind,
        'sourceId': sourceId,
      },
      decode: (json) => MvpRuntimeItemDetail.fromJson(json as Map<String, dynamic>),
    );
  }

  Future<ApiResult<void>> snoozeItem({
    required String sourceKind,
    required String sourceId,
    required String snoozedUntil,
  }) async {
    return _client.request<void>(
      MvpEndpoint.workspaceRuntimeItemSnooze,
      pathParams: {
        'sourceKind': sourceKind,
        'sourceId': sourceId,
      },
      body: {
        'snoozedUntil': snoozedUntil,
      },
      decode: (_) {},
    );
  }

  Future<ApiResult<List<MvpSourceStatus>>> getSourceStatus() async {
    return _client.request<List<MvpSourceStatus>>(
      MvpEndpoint.workspaceRuntimeSourceStatus,
      decode: (json) {
        final list = json is List ? json : (json as Map<String, dynamic>)['items'] as List? ?? [];
        return list
            .whereType<Map<String, dynamic>>()
            .map((e) => MvpSourceStatus.fromJson(e))
            .toList();
      },
    );
  }
}
