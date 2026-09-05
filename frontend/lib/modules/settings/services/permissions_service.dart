import 'package:http/http.dart' as http;
import '../../../core/network/api_result.dart';
import '../../../core/network/mvp_endpoints.g.dart';
import '../../../core/network/mvp_request_client.dart';
import '../models/permission_models.dart';

class PermissionsService {
  final MvpRequestClient _client;

  PermissionsService({MvpRequestClient? client, http.Client? httpClient})
      : _client = client ?? MvpRequestClient(httpClient: httpClient);

  Future<ApiResult<PermissionsDataModel>> getPermissions() async {
    return _client.request<PermissionsDataModel>(
      MvpEndpoint.settingsPermissionGet,
      decode: (json) => PermissionsDataModel.fromJson(json as Map<String, dynamic>),
    );
  }

  Future<ApiResult<SimulatePermissionsResponse>> simulatePermissions({
    required String action,
    String? memberId,
    String? projectId,
    String? legalEntityId,
    Map<String, dynamic>? facts,
  }) async {
    return _client.request<SimulatePermissionsResponse>(
      MvpEndpoint.settingsPermissionSimulate,
      body: {
        'action': action,
        'memberId': ?memberId,
        'projectId': ?projectId,
        'legalEntityId': ?legalEntityId,
        'facts': ?facts,
      },
      decode: (json) =>
          SimulatePermissionsResponse.fromJson(json as Map<String, dynamic>),
    );
  }

  Future<ApiResult<Map<String, dynamic>>> updatePermissions({
    required int expectedVersion,
    required String reason,
    required List<Map<String, dynamic>> mutations,
  }) async {
    return _client.request<Map<String, dynamic>>(
      MvpEndpoint.settingsPermissionUpdate,
      body: {
        'expectedVersion': expectedVersion,
        'reason': reason,
        'mutations': mutations,
      },
      decode: (json) => (json as Map<String, dynamic>?) ?? {},
    );
  }
}
