// Founder Trial R1 — legacy surface removed from the MVP contract. Every
// request here now returns MvpRequestClient.unavailable(); the retained
// class shell keeps callers compiling until the module is deleted.
// ignore_for_file: unused_field, unused_import, unused_element
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
    return MvpRequestClient.unavailable<PermissionsDataModel>('settingsPermissionGet was removed from the Founder Trial R1 contract');
  }

  Future<ApiResult<SimulatePermissionsResponse>> simulatePermissions({
    required String action,
    String? memberId,
    String? projectId,
    String? legalEntityId,
    Map<String, dynamic>? facts,
  }) async {
    return MvpRequestClient.unavailable<SimulatePermissionsResponse>('settingsPermissionSimulate was removed from the Founder Trial R1 contract');
  }

  Future<ApiResult<Map<String, dynamic>>> updatePermissions({
    required int expectedVersion,
    required String reason,
    required List<Map<String, dynamic>> mutations,
  }) async {
    return MvpRequestClient.unavailable<Map<String, dynamic>>('settingsPermissionUpdate was removed from the Founder Trial R1 contract');
  }
}
