import 'dart:convert';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:frontend/core/network/api_result.dart';
import 'package:frontend/core/network/mvp_request_client.dart';
import 'package:frontend/modules/workspace_runtime/services/workspace_runtime_mvp_client.dart';
import 'package:frontend/modules/workspace_runtime/models/mvp_runtime_models.dart';

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({
      'auth_token': 'test-token',
      'workspace_id': 'ws_1001',
    });
  });

  test('empty runtime response keeps source status and renders an empty state', () async {
    final mockHttp = MockClient((request) async {
      return http.Response(
        jsonEncode({
          'data': [],
          'meta': {
            'dataState': 'empty',
            'observedAt': '2026-08-31T12:00:00.000Z',
            'sources': [{'kind': 'company_db', 'ref': 'operating.tasks'}],
          },
        }),
        200,
      );
    });

    final requestClient = MvpRequestClient(httpClient: mockHttp);
    final runtime = WorkspaceRuntimeMvpClient(client: requestClient);

    final result = await runtime.listNeedsYou();
    expect(result, isA<ApiSuccess<List<MvpRuntimeItem>>>());
    final success = result as ApiSuccess<List<MvpRuntimeItem>>;
    expect(success.data, isEmpty);
    expect(success.meta.dataState, ApiDataState.empty);
  });

  test('runtime blockers failure preserves ApiFailure and does not collapse to empty', () async {
    final mockHttp = MockClient((request) async {
      return http.Response(
        jsonEncode({'code': 'permission_denied', 'message': 'Access forbidden'}),
        403,
      );
    });

    final requestClient = MvpRequestClient(httpClient: mockHttp);
    final runtime = WorkspaceRuntimeMvpClient(client: requestClient);

    final result = await runtime.listBlockers();
    expect(result, isA<ApiFailure<List<MvpRuntimeItem>>>());
    final failure = result as ApiFailure<List<MvpRuntimeItem>>;
    expect(failure.failure.code, ApiFailureCode.forbidden);
  });
}
