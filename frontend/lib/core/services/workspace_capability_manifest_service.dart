import 'package:http/http.dart' as http;

import '../network/api_result.dart';
import '../network/mvp_endpoints.g.dart';
import '../network/mvp_request_client.dart';
import 'workspace_capability_manifest_model.dart';

/// Interface để controller/test không phụ thuộc vào HTTP thật.
abstract class WorkspaceCapabilityManifestApi {
  Future<ApiResult<WorkspaceCapabilityManifest>> fetch();
}

/// Đọc `WorkspaceCapabilityManifest` từ Control Plane qua endpoint typed.
class WorkspaceCapabilityManifestService implements WorkspaceCapabilityManifestApi {
  WorkspaceCapabilityManifestService({MvpRequestClient? client, http.Client? httpClient})
      : _client = client ?? MvpRequestClient(httpClient: httpClient);

  final MvpRequestClient _client;

  @override
  Future<ApiResult<WorkspaceCapabilityManifest>> fetch() {
    return _client.request<WorkspaceCapabilityManifest>(
      MvpEndpoint.settingsCapabilityManifestRead,
      decode: (json) =>
          WorkspaceCapabilityManifest.fromJson(json as Map<String, dynamic>),
    );
  }
}
