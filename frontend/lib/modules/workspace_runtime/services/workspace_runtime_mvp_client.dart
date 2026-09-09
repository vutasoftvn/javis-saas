// Founder Trial R1 — legacy surface removed from the MVP contract. Every
// request here now returns MvpRequestClient.unavailable(); the retained
// class shell keeps callers compiling until the module is deleted.
// ignore_for_file: unused_field, unused_import, unused_element
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
    return MvpRequestClient.unavailable<List<MvpRuntimeItem>>('workspaceRuntimeNeedsYou was removed from the Founder Trial R1 contract');
  }

  Future<ApiResult<List<MvpRuntimeItem>>> listBlockers() async {
    return MvpRequestClient.unavailable<List<MvpRuntimeItem>>('workspaceRuntimeBlockers was removed from the Founder Trial R1 contract');
  }

  Future<ApiResult<MvpRuntimeItemDetail>> getItem({
    required String sourceKind,
    required String sourceId,
  }) async {
    return MvpRequestClient.unavailable<MvpRuntimeItemDetail>('workspaceRuntimeItemGet was removed from the Founder Trial R1 contract');
  }

  Future<ApiResult<void>> snoozeItem({
    required String sourceKind,
    required String sourceId,
    required String snoozedUntil,
  }) async {
    return MvpRequestClient.unavailable<void>('workspaceRuntimeItemSnooze was removed from the Founder Trial R1 contract');
  }

  Future<ApiResult<List<MvpSourceStatus>>> getSourceStatus() async {
    return MvpRequestClient.unavailable<List<MvpSourceStatus>>('workspaceRuntimeSourceStatus was removed from the Founder Trial R1 contract');
  }
}
