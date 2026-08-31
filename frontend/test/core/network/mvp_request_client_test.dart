import 'dart:convert';
import 'dart:io';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:frontend/core/network/api_auth_resolver.dart';
import 'package:frontend/core/network/api_result.dart';
import 'package:frontend/core/network/mvp_endpoints.g.dart';
import 'package:frontend/core/network/mvp_request_client.dart';

class _FakeAuthResolver implements ApiAuthResolver {
  _FakeAuthResolver({this.token, this.wsId});
  final String? token;
  final String? wsId;

  @override
  Future<String?> tokenFor(ApiPlane plane) async => token;

  @override
  Future<String?> workspaceId() async => wsId;
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() async {
    SharedPreferences.setMockInitialValues({
      'auth_token': 'test_token_123',
      'workspace_id': '1001',
    });
  });

  group('MvpRequestClient', () {
    test('403 remains forbidden rather than an empty success', () async {
      final mockHttp = MockClient((request) async {
        return http.Response(
          jsonEncode({'error': 'Forbidden access'}),
          403,
          headers: {'content-type': 'application/json'},
        );
      });

      final client = MvpRequestClient(httpClient: mockHttp);
      final result = await client.request<List<String>>(
        MvpEndpoint.strategyCanvasList,
        decode: (json) => (json as List<dynamic>).cast<String>(),
      );

      expect(result, isA<ApiFailure<List<String>>>());
      final failure = (result as ApiFailure<List<String>>).failure;
      expect(failure.code, ApiFailureCode.forbidden);
      expect(failure.statusCode, 403);
    });

    test('a successful empty envelope remains empty with metadata', () async {
      final mockHttp = MockClient((request) async {
        return http.Response(
          jsonEncode({
            'data': [],
            'meta': {
              'data_state': 'empty',
              'observed_at': '2026-08-31T12:00:00.000Z',
              'sources': [
                {'kind': 'company_db', 'ref': 'strategy.canvases'}
              ],
            },
          }),
          200,
          headers: {'content-type': 'application/json'},
        );
      });

      final client = MvpRequestClient(httpClient: mockHttp);
      final result = await client.request<List<String>>(
        MvpEndpoint.strategyCanvasList,
        decode: (json) => (json as List<dynamic>).cast<String>(),
      );

      expect(result, isA<ApiSuccess<List<String>>>());
      final success = result as ApiSuccess<List<String>>;
      expect(success.data, isEmpty);
      expect(success.meta.dataState, ApiDataState.empty);
    });

    test('a successful populated envelope decodes items and meta', () async {
      final mockHttp = MockClient((request) async {
        return http.Response(
          jsonEncode({
            'data': ['canvas-1', 'canvas-2'],
            'meta': {
              'data_state': 'populated',
              'observed_at': '2026-08-31T12:00:00.000Z',
              'sources': [
                {'kind': 'company_db', 'ref': 'strategy.canvases'}
              ],
            },
          }),
          200,
          headers: {'content-type': 'application/json'},
        );
      });

      final client = MvpRequestClient(httpClient: mockHttp);
      final result = await client.request<List<String>>(
        MvpEndpoint.strategyCanvasList,
        decode: (json) => (json as List<dynamic>).cast<String>(),
      );

      expect(result, isA<ApiSuccess<List<String>>>());
      final success = result as ApiSuccess<List<String>>;
      expect(success.data, ['canvas-1', 'canvas-2']);
      expect(success.meta.dataState, ApiDataState.populated);
    });

    test('missing auth token fails unauthenticated', () async {
      final client = MvpRequestClient(
        authResolver: _FakeAuthResolver(token: null, wsId: '1001'),
      );
      final result = await client.request<List<String>>(
        MvpEndpoint.strategyCanvasList,
        decode: (json) => (json as List<dynamic>).cast<String>(),
      );

      expect(result, isA<ApiFailure<List<String>>>());
      expect((result as ApiFailure<List<String>>).failure.code, ApiFailureCode.unauthenticated);
    });

    test('missing workspace fails invalidRequest', () async {
      final client = MvpRequestClient(
        authResolver: _FakeAuthResolver(token: 'valid_tok', wsId: null),
      );
      final result = await client.request<List<String>>(
        MvpEndpoint.strategyCanvasList,
        decode: (json) => (json as List<dynamic>).cast<String>(),
      );

      expect(result, isA<ApiFailure<List<String>>>());
      expect((result as ApiFailure<List<String>>).failure.code, ApiFailureCode.invalidRequest);
    });

    test('malformed envelope returns ApiFailureCode.malformedResponse', () async {
      final mockHttp = MockClient((request) async {
        return http.Response('not a json envelope', 200, headers: {'content-type': 'application/json'});
      });

      final client = MvpRequestClient(
        httpClient: mockHttp,
        authResolver: _FakeAuthResolver(token: 'valid_tok', wsId: '1001'),
      );
      final result = await client.request<List<String>>(
        MvpEndpoint.strategyCanvasList,
        decode: (json) => (json as List<dynamic>).cast<String>(),
      );

      expect(result, isA<ApiFailure<List<String>>>());
      expect((result as ApiFailure<List<String>>).failure.code, ApiFailureCode.malformedResponse);
    });

    test('network exception returns ApiFailureCode.unavailable', () async {
      final mockHttp = MockClient((request) async {
        throw const SocketException('Connection refused');
      });

      final client = MvpRequestClient(
        httpClient: mockHttp,
        authResolver: _FakeAuthResolver(token: 'valid_tok', wsId: '1001'),
      );
      final result = await client.request<List<String>>(
        MvpEndpoint.strategyCanvasList,
        decode: (json) => (json as List<dynamic>).cast<String>(),
      );

      expect(result, isA<ApiFailure<List<String>>>());
      expect((result as ApiFailure<List<String>>).failure.code, ApiFailureCode.unavailable);
    });
  });
}
