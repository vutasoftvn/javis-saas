import 'dart:convert';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:frontend/core/network/api_result.dart';
import 'package:frontend/core/network/mvp_request_client.dart';
import 'package:frontend/core/services/secure_storage_service.dart';
import 'package:frontend/modules/strategy/services/strategy_mvp_client.dart';
import 'package:frontend/modules/strategy/models/mvp_strategy_models.dart';

void main() {
  setUp(() async {
    SharedPreferences.setMockInitialValues({
      'workspace_id': 'ws_1001',
    });
    await SecureStorageService.write('auth_token', 'test-token');
  });

  test('canvas 503 is unavailable, not an empty canvas collection', () async {
    final mockHttp = MockClient((request) async {
      return http.Response(
        jsonEncode({'code': 'unavailable', 'message': 'Service temporarily unavailable'}),
        503,
      );
    });

    final requestClient = MvpRequestClient(httpClient: mockHttp);
    final service = StrategyMvpClient(client: requestClient);

    final result = await service.listCanvases();
    expect(result, isA<ApiFailure<List<MvpCanvas>>>());
    expect((result as ApiFailure<List<MvpCanvas>>).failure.code, ApiFailureCode.unavailable);
  });

  test('empty canvas response returns ApiSuccess with empty dataState', () async {
    final mockHttp = MockClient((request) async {
      return http.Response(
        jsonEncode({
          'data': [],
          'meta': {
            'dataState': 'empty',
            'observedAt': '2026-08-31T12:00:00.000Z',
            'sources': [{'kind': 'company_db', 'ref': 'strategy.canvases'}],
          },
        }),
        200,
      );
    });

    final requestClient = MvpRequestClient(httpClient: mockHttp);
    final service = StrategyMvpClient(client: requestClient);

    final result = await service.listCanvases();
    expect(result, isA<ApiSuccess<List<MvpCanvas>>>());
    final success = result as ApiSuccess<List<MvpCanvas>>;
    expect(success.data, isEmpty);
    expect(success.meta.dataState, ApiDataState.empty);
    expect(success.meta.sources.first.kind, 'company_db');
  });

  test('populated canvas response returns typed objects and populated dataState', () async {
    final mockHttp = MockClient((request) async {
      return http.Response(
        jsonEncode({
          'data': [
            {
              'id': 'canvas_1',
              'workspaceId': 'ws_1001',
              'name': 'Lean Canvas',
              'description': 'Product Model',
              'createdAt': '2026-08-31T12:00:00.000Z',
              'updatedAt': '2026-08-31T12:00:00.000Z',
            }
          ],
          'meta': {
            'dataState': 'populated',
            'observedAt': '2026-08-31T12:00:00.000Z',
            'sources': [{'kind': 'company_db', 'ref': 'strategy.canvases'}],
          },
        }),
        200,
      );
    });

    final requestClient = MvpRequestClient(httpClient: mockHttp);
    final service = StrategyMvpClient(client: requestClient);

    final result = await service.listCanvases();
    expect(result, isA<ApiSuccess<List<MvpCanvas>>>());
    final success = result as ApiSuccess<List<MvpCanvas>>;
    expect(success.data.length, 1);
    expect(success.data.first.name, 'Lean Canvas');
    expect(success.meta.dataState, ApiDataState.populated);
  });
}
