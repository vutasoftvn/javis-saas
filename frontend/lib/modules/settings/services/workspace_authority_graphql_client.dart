import 'dart:convert';
import 'package:http/http.dart' as http;
import '../../../core/network/api_auth_resolver.dart';
import '../../../core/network/api_client.dart';
import '../../../core/network/api_result.dart';
import '../models/permission_models.dart';

class WorkspaceAuthorityGraphqlClient {
  final http.Client _httpClient;
  final ApiAuthResolver _authResolver;

  WorkspaceAuthorityGraphqlClient({
    http.Client? httpClient,
    ApiAuthResolver? authResolver,
  })  : _httpClient = httpClient ?? http.Client(),
        _authResolver = authResolver ?? const DefaultApiAuthResolver();

  Future<ApiResult<WorkspaceAuthorityOverviewModel>> fetchOverview() async {
    final token = await _authResolver.tokenFor(ApiPlane.agent);
    final workspaceId = await _authResolver.workspaceId();

    final target = ApiClient.resolveRequestTarget('/agent/graphql');
    if (target.blockedResponse case final blocked?) {
      return ApiFailure(
        ApiFailureDetail(
          code: ApiFailureCode.unavailable,
          statusCode: blocked.statusCode,
          message: blocked.body,
        ),
      );
    }

    final uri = target.uri!;
    final headers = <String, String>{
      'Content-Type': 'application/json',
      'Accept': 'application/json',
      if (token != null && token.isNotEmpty) 'Authorization': 'Bearer $token',
      if (workspaceId != null && workspaceId.isNotEmpty) 'X-Workspace-Id': workspaceId,
    };

    final body = jsonEncode({
      'operationId': 'workspaceAuthorityOverview',
      'variables': <String, dynamic>{},
    });

    try {
      final response = await _httpClient.post(uri, headers: headers, body: body);

      if (response.statusCode >= 200 && response.statusCode < 300) {
        final decoded = jsonDecode(response.body) as Map<String, dynamic>;
        final data = decoded['data'] as Map<String, dynamic>? ?? {};
        final overviewData = data['workspaceAuthorityOverview'] as Map<String, dynamic>? ?? {};
        return ApiSuccess(
          data: WorkspaceAuthorityOverviewModel.fromJson(overviewData),
          meta: ApiResponseMeta(
            dataState: ApiDataState.populated,
            observedAt: DateTime.now(),
            sources: const [],
          ),
        );
      }

      if (response.statusCode == 403) {
        return const ApiFailure(
          ApiFailureDetail(
            code: ApiFailureCode.forbidden,
            statusCode: 403,
            message: 'Founder authority required',
          ),
        );
      }

      if (response.statusCode == 409) {
        return const ApiFailure(
          ApiFailureDetail(
            code: ApiFailureCode.conflict,
            statusCode: 409,
            message: 'Authority state conflict',
          ),
        );
      }

      if (response.statusCode == 422) {
        return const ApiFailure(
          ApiFailureDetail(
            code: ApiFailureCode.invalidRequest,
            statusCode: 422,
            message: 'Invalid GraphQL operation or variables',
          ),
        );
      }

      return ApiFailure(
        ApiFailureDetail(
          code: ApiFailureCode.unknown,
          statusCode: response.statusCode,
          message: 'GraphQL request failed: ${response.statusCode}',
        ),
      );
    } catch (e) {
      return ApiFailure(
        ApiFailureDetail(
          code: ApiFailureCode.notConnected,
          message: e.toString(),
        ),
      );
    }
  }
}
