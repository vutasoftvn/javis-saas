import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'package:http/http.dart' as http;

import 'api_auth_resolver.dart';
import 'api_client.dart';
import 'api_result.dart';
import 'mvp_endpoints.g.dart';

class MvpRequestClient {
  MvpRequestClient({
    http.Client? httpClient,
    ApiAuthResolver? authResolver,
  })  : _httpClient = httpClient ?? http.Client(),
        _authResolver = authResolver ?? const DefaultApiAuthResolver();

  final http.Client _httpClient;
  final ApiAuthResolver _authResolver;

  String _resolveBaseUrl(ApiPlane plane) {
    switch (plane) {
      case ApiPlane.company:
        return ApiClient.baseUrl;
      case ApiPlane.platform:
        return ApiClient.platformBaseUrl;
      case ApiPlane.agent:
        return ApiClient.agentOsBaseUrl;
      case ApiPlane.localWorker:
        return ApiClient.desktopWorkerBaseUrl;
    }
  }

  String _buildPath(String pathTemplate, Map<String, String>? pathParams) {
    if (pathParams == null || pathParams.isEmpty) {
      return pathTemplate;
    }
    var resolved = pathTemplate;
    pathParams.forEach((key, value) {
      resolved = resolved.replaceAll(':$key', Uri.encodeComponent(value));
    });
    return resolved;
  }

  Future<ApiResult<T>> request<T>(
    MvpEndpoint endpoint, {
    Map<String, String>? pathParams,
    Map<String, String>? query,
    Object? body,
    required T Function(Object?) decode,
  }) async {
    try {
      final token = await _authResolver.tokenFor(endpoint.plane);
      final workspaceId = await _authResolver.workspaceId();

      if (endpoint.requiresWorkspace && (token == null || token.isEmpty)) {
        return const ApiFailure(ApiFailureDetail(
          code: ApiFailureCode.unauthenticated,
          statusCode: 401,
          message: 'Missing authentication token',
        ));
      }

      if (endpoint.requiresWorkspace && (workspaceId == null || workspaceId.isEmpty)) {
        return const ApiFailure(ApiFailureDetail(
          code: ApiFailureCode.invalidRequest,
          statusCode: 400,
          message: 'Missing workspace context',
        ));
      }

      final base = _resolveBaseUrl(endpoint.plane);
      var effectivePath = _buildPath(endpoint.path, pathParams);
      if (effectivePath.contains(':workspaceId') && workspaceId != null) {
        effectivePath = effectivePath.replaceAll(':workspaceId', Uri.encodeComponent(workspaceId));
      }

      var uri = Uri.parse('$base$effectivePath');
      if (query != null && query.isNotEmpty) {
        uri = uri.replace(queryParameters: {
          ...uri.queryParameters,
          ...query,
        });
      }

      final headers = <String, String>{
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      };
      if (token != null && token.isNotEmpty) {
        headers['Authorization'] = 'Bearer $token';
      }
      if (workspaceId != null && workspaceId.isNotEmpty) {
        headers['X-Workspace-Id'] = workspaceId;
      }

      final http.Response response;
      final encodedBody = body != null ? jsonEncode(body) : null;

      switch (endpoint.method.toUpperCase()) {
        case 'GET':
          response = await _httpClient.get(uri, headers: headers);
          break;
        case 'POST':
          response = await _httpClient.post(uri, headers: headers, body: encodedBody);
          break;
        case 'PUT':
          response = await _httpClient.put(uri, headers: headers, body: encodedBody);
          break;
        case 'PATCH':
          response = await _httpClient.patch(uri, headers: headers, body: encodedBody);
          break;
        case 'DELETE':
          response = await _httpClient.delete(uri, headers: headers, body: encodedBody);
          break;
        default:
          return ApiFailure(ApiFailureDetail(
            code: ApiFailureCode.invalidRequest,
            message: 'Unsupported HTTP method: ${endpoint.method}',
            endpointId: endpoint.id,
          ));
      }

      return _decodeResponse<T>(response, endpoint, decode);
    } on SocketException catch (e) {
      return ApiFailure(ApiFailureDetail(
        code: ApiFailureCode.unavailable,
        message: 'Network connection failed: ${e.message}',
        endpointId: endpoint.id,
      ));
    } on TimeoutException catch (e) {
      return ApiFailure(ApiFailureDetail(
        code: ApiFailureCode.unavailable,
        message: 'Request timed out: ${e.message}',
        endpointId: endpoint.id,
      ));
    } catch (e) {
      return ApiFailure(ApiFailureDetail(
        code: ApiFailureCode.unknown,
        message: e.toString(),
        endpointId: endpoint.id,
      ));
    }
  }

  ApiResult<T> _decodeResponse<T>(
    http.Response response,
    MvpEndpoint endpoint,
    T Function(Object?) decode,
  ) {
    final status = response.statusCode;
    if (status >= 200 && status < 300) {
      try {
        final decoded = jsonDecode(utf8.decode(response.bodyBytes));
        if (decoded is! Map<String, dynamic>) {
          return ApiFailure(ApiFailureDetail(
            code: ApiFailureCode.malformedResponse,
            statusCode: status,
            message: 'Expected JSON object envelope but got ${decoded.runtimeType}',
            endpointId: endpoint.id,
          ));
        }

        if (!decoded.containsKey('data') || !decoded.containsKey('meta')) {
          return ApiFailure(ApiFailureDetail(
            code: ApiFailureCode.malformedResponse,
            statusCode: status,
            message: 'Missing "data" or "meta" in success envelope',
            endpointId: endpoint.id,
          ));
        }

        final meta = ApiResponseMeta.fromJson(decoded['meta'] as Map<String, dynamic>);
        final data = decode(decoded['data']);
        return ApiSuccess(data: data, meta: meta);
      } catch (e) {
        return ApiFailure(ApiFailureDetail(
          code: ApiFailureCode.malformedResponse,
          statusCode: status,
          message: 'Failed to parse response: $e',
          endpointId: endpoint.id,
        ));
      }
    }

    // Map non-2xx status codes
    final ApiFailureCode code;
    switch (status) {
      case 401:
        code = ApiFailureCode.unauthenticated;
        break;
      case 403:
        code = ApiFailureCode.forbidden;
        break;
      case 404:
        code = ApiFailureCode.notFound;
        break;
      case 409:
        code = ApiFailureCode.conflict;
        break;
      case 429:
        code = ApiFailureCode.rateLimited;
        break;
      default:
        if (status >= 400 && status < 500) {
          code = ApiFailureCode.invalidRequest;
        } else {
          code = ApiFailureCode.unavailable;
        }
    }

    String message = 'HTTP $status';
    try {
      final bodyObj = jsonDecode(utf8.decode(response.bodyBytes));
      if (bodyObj is Map<String, dynamic>) {
        if (bodyObj['message'] is String) {
          message = bodyObj['message'] as String;
        } else if (bodyObj['error'] is String) {
          message = bodyObj['error'] as String;
        } else if (bodyObj['detail'] is String) {
          message = bodyObj['detail'] as String;
        }
      }
    } catch (_) {}

    return ApiFailure(ApiFailureDetail(
      code: code,
      statusCode: status,
      message: message,
      endpointId: endpoint.id,
      raw: response.body,
    ));
  }
}
