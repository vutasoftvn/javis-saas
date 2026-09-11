import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/core/network/api_result.dart';
import 'package:frontend/core/network/mvp_endpoints.g.dart';
import 'package:frontend/core/network/mvp_request_client.dart';
import 'package:frontend/modules/settings/models/permission_models.dart';
import 'package:frontend/modules/settings/services/permissions_service.dart';
import 'package:frontend/modules/settings/services/workspace_authority_graphql_client.dart';

class FakeMvpRequestClient extends MvpRequestClient {
  MvpEndpoint? lastEndpoint;
  Object? lastBody;
  Map<String, String>? lastPathParams;

  @override
  Future<ApiResult<T>> request<T>(
    MvpEndpoint endpoint, {
    Map<String, String>? pathParams,
    Map<String, String>? query,
    Object? body,
    required T Function(Object? p1) decode,
  }) async {
    lastEndpoint = endpoint;
    lastBody = body;
    lastPathParams = pathParams;

    if (endpoint == MvpEndpoint.identityAgentCapabilityGrantCreate) {
      final mockData = {
        'id': 'grant-123',
        'workspaceId': 'ws-1',
        'agentWorkforceMemberId': '77',
        'capabilityId': 'operations.task.list',
        'status': 'ACTIVE',
        'validFrom': '2026-09-11T00:00:00Z',
      };
      return ApiSuccess(
        data: decode(mockData),
        meta: ApiResponseMeta(
          dataState: ApiDataState.populated,
          observedAt: DateTime.now(),
          sources: const [],
        ),
      );
    }

    if (endpoint == MvpEndpoint.identityAgentCapabilityGrantRevoke) {
      return ApiSuccess(
        data: decode({'success': true}),
        meta: ApiResponseMeta(
          dataState: ApiDataState.populated,
          observedAt: DateTime.now(),
          sources: const [],
        ),
      );
    }

    return const ApiFailure(
      ApiFailureDetail(code: ApiFailureCode.unknown, message: 'unmocked'),
    );

  }
}

class FakeWorkspaceAuthorityGraphqlClient extends WorkspaceAuthorityGraphqlClient {
  Map<String, dynamic>? lastBody;

  @override
  Future<ApiResult<WorkspaceAuthorityOverviewModel>> fetchOverview() async {
    lastBody = {'operationId': 'workspaceAuthorityOverview', 'variables': {}};
    return ApiSuccess(
      data: const WorkspaceAuthorityOverviewModel(
        roles: [],
        assignments: [],
        grants: [],
        bindings: [],
        events: [],
        members: [],
        authorizationEpoch: 1,
        policyVersion: 1,
      ),
      meta: ApiResponseMeta(
        dataState: ApiDataState.populated,
        observedAt: DateTime.now(),
        sources: const [],
      ),
    );
  }
}

void main() {
  test('founder loads persisted overview and sends grant command through generated endpoint', () async {
    final fakeMvpClient = FakeMvpRequestClient();
    final fakeGraphqlClient = FakeWorkspaceAuthorityGraphqlClient();

    final service = PermissionsService(
      client: fakeMvpClient,
      graphqlClient: fakeGraphqlClient,
    );

    await service.fetchOverview();
    expect(fakeGraphqlClient.lastBody, {'operationId': 'workspaceAuthorityOverview', 'variables': {}});

    final result = await service.createAgentCapabilityGrant(
      agentWorkforceMemberId: '77',
      capabilityId: 'operations.task.list',
    );

    expect(result, isA<ApiSuccess<AgentCapabilityGrantModel>>());
    expect(fakeMvpClient.lastEndpoint, MvpEndpoint.identityAgentCapabilityGrantCreate);
  });
}
