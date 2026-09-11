import 'package:http/http.dart' as http;
import '../../../core/network/api_result.dart';
import '../../../core/network/mvp_endpoints.g.dart';
import '../../../core/network/mvp_request_client.dart';
import '../models/permission_models.dart';
import 'workspace_authority_graphql_client.dart';

class PermissionsService {
  final MvpRequestClient _client;
  final WorkspaceAuthorityGraphqlClient _graphqlClient;

  PermissionsService({
    MvpRequestClient? client,
    WorkspaceAuthorityGraphqlClient? graphqlClient,
    http.Client? httpClient,
  })  : _client = client ?? MvpRequestClient(httpClient: httpClient),
        _graphqlClient = graphqlClient ?? WorkspaceAuthorityGraphqlClient(httpClient: httpClient);

  Future<ApiResult<WorkspaceAuthorityOverviewModel>> fetchOverview() async {
    return _graphqlClient.fetchOverview();
  }

  Future<ApiResult<PermissionsDataModel>> getPermissions() async {
    return _client.request<PermissionsDataModel>(
      MvpEndpoint.identityPermissionsRead,
      decode: (raw) => PermissionsDataModel.fromJson(raw as Map<String, dynamic>),
    );
  }

  Future<ApiResult<SimulatePermissionsResponse>> simulatePermissions({
    required String action,
    String? memberId,
    String? projectId,
    String? legalEntityId,
    Map<String, dynamic>? facts,
  }) async {
    final body = <String, dynamic>{'action': action};
    if (memberId != null) body['memberId'] = memberId;
    if (projectId != null) body['projectId'] = projectId;
    if (legalEntityId != null) body['legalEntityId'] = legalEntityId;
    if (facts != null) body['facts'] = facts;

    return _client.request<SimulatePermissionsResponse>(
      MvpEndpoint.identityPermissionsSimulate,
      body: body,
      decode: (raw) => SimulatePermissionsResponse.fromJson(raw as Map<String, dynamic>),
    );
  }

  Future<ApiResult<Map<String, dynamic>>> updatePermissions({
    required int expectedVersion,
    required String reason,
    required List<Map<String, dynamic>> mutations,
  }) async {
    final body = <String, dynamic>{
      'expectedVersion': expectedVersion,
      'reason': reason,
      'mutations': mutations,
    };
    return _client.request<Map<String, dynamic>>(
      MvpEndpoint.identityPermissionsWrite,
      body: body,
      decode: (raw) => (raw as Map<String, dynamic>? ?? {}),
    );
  }

  Future<ApiResult<AgentCapabilityGrantModel>> createAgentCapabilityGrant({
    required String agentWorkforceMemberId,
    required String capabilityId,
    String? projectId,
    String? legalEntityId,
    Map<String, dynamic>? constraints,
    String? validUntil,
  }) async {
    final body = <String, dynamic>{
      'agentWorkforceMemberId': agentWorkforceMemberId,
      'capabilityId': capabilityId,
    };
    if (projectId != null) body['projectId'] = projectId;
    if (legalEntityId != null) body['legalEntityId'] = legalEntityId;
    if (constraints != null) body['constraints'] = constraints;
    if (validUntil != null) body['validUntil'] = validUntil;

    return _client.request<AgentCapabilityGrantModel>(
      MvpEndpoint.identityAgentCapabilityGrantCreate,
      body: body,
      decode: (raw) => AgentCapabilityGrantModel.fromJson(raw as Map<String, dynamic>),
    );
  }

  Future<ApiResult<Map<String, dynamic>>> revokeAgentCapabilityGrant({
    required String grantId,
    required String reason,
  }) async {
    return _client.request<Map<String, dynamic>>(
      MvpEndpoint.identityAgentCapabilityGrantRevoke,
      pathParams: {'grantId': grantId},
      body: {'reason': reason},
      decode: (raw) => (raw as Map<String, dynamic>? ?? {}),
    );
  }
}
