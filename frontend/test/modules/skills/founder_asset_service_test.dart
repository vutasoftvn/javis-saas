import 'dart:convert';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:frontend/core/network/api_result.dart';
import 'package:frontend/core/network/mvp_request_client.dart';
import 'package:frontend/core/services/secure_storage_service.dart';
import 'package:frontend/modules/skills/models/founder_asset.dart';
import 'package:frontend/modules/skills/services/founder_asset_service.dart';

void main() {
  setUp(() async {
    SharedPreferences.setMockInitialValues({'workspace_id': '1001'});
    await SecureStorageService.write('auth_token', 'test-token');
  });

  test('lists the founder asset library through the generated endpoint', () async {
    final mockHttp = MockClient((request) async {
      expect(request.method, 'GET');
      expect(request.url.path, '/operations/founder-assets');

      return http.Response(
        jsonEncode({
          'data': [
            {
              'assetId': 'skill.custom.summary',
              'assetKind': 'SKILL',
              'originAssetId': 'skill.builtin.summary',
              'version': '1',
              'definitionHash': 'sha256:abc',
              'lifecycle': 'DRAFT',
              'lastOperation': 'CLONE',
              'deployments': {'active': 0, 'paused': 0, 'retired': 0},
            },
          ],
          'meta': {
            'dataState': 'populated',
            'observedAt': '2026-09-14T00:00:00Z',
            'sources': [
              {'kind': 'company_db', 'ref': 'operations.founder_asset_events'},
            ],
          },
        }),
        200,
        headers: {'content-type': 'application/json'},
      );
    });

    final service = FounderAssetService(client: MvpRequestClient(httpClient: mockHttp));
    final result = await service.listLibrary();

    expect(result, isA<ApiSuccess<List<FounderAssetLibraryItem>>>());
    final items = (result as ApiSuccess<List<FounderAssetLibraryItem>>).data;
    expect(items, hasLength(1));
    expect(items.first.assetKind, FounderAssetKind.skill);
    expect(items.first.originAssetId, 'skill.builtin.summary');
    expect(items.first.lifecycle, 'DRAFT');
  });

  test('clones a built-in skill into a workspace draft', () async {
    final mockHttp = MockClient((request) async {
      expect(request.method, 'POST');
      expect(request.url.path, '/operations/founder/assets/commands');
      final body = jsonDecode(request.body) as Map<String, dynamic>;
      expect(body['assetKind'], 'SKILL');
      expect(body['operation'], 'CLONE');
      expect(body['assetRef'], {'assetId': 'skill.builtin.summary', 'version': '1'});
      expect(body['reason'], 'Tuỳ biến cho workspace');
      expect(body['idempotencyKey'], isNotEmpty);

      return http.Response(
        jsonEncode({
          'data': {
            'commandId': 'cmd-1',
            'assetKind': 'SKILL',
            'operation': 'CLONE',
            'status': 'PENDING',
            'idempotencyKey': body['idempotencyKey'],
          },
          'meta': {
            'dataState': 'populated',
            'observedAt': '2026-09-14T00:00:00Z',
            'sources': [
              {'kind': 'company_db', 'ref': 'operations.founder_asset_events'},
            ],
          },
        }),
        200,
        headers: {'content-type': 'application/json'},
      );
    });

    final service = FounderAssetService(client: MvpRequestClient(httpClient: mockHttp));
    final result = await service.cloneAsset(
      assetKind: FounderAssetKind.skill,
      sourceAssetId: 'skill.builtin.summary',
      sourceVersion: '1',
      reason: 'Tuỳ biến cho workspace',
    );

    expect(result, isA<ApiSuccess<FounderAssetCommandResult>>());
    final cmd = (result as ApiSuccess<FounderAssetCommandResult>).data;
    expect(cmd.operation, 'CLONE');
    expect(cmd.status, 'PENDING');
  });

  test('publishes a draft with the exact asset ref (id + version + hash)', () async {
    final mockHttp = MockClient((request) async {
      expect(request.method, 'POST');
      final body = jsonDecode(request.body) as Map<String, dynamic>;
      expect(body['operation'], 'PUBLISH');
      expect(body['assetRef'], {
        'assetId': 'skill.custom.summary',
        'version': '1',
        'definitionHash': 'sha256:abc',
      });

      return http.Response(
        jsonEncode({
          'data': {
            'commandId': 'cmd-2',
            'assetKind': 'SKILL',
            'operation': 'PUBLISH',
            'status': 'PENDING',
            'idempotencyKey': body['idempotencyKey'],
          },
          'meta': {
            'dataState': 'populated',
            'observedAt': '2026-09-14T00:00:00Z',
            'sources': [
              {'kind': 'company_db', 'ref': 'operations.founder_asset_events'},
            ],
          },
        }),
        200,
        headers: {'content-type': 'application/json'},
      );
    });

    final service = FounderAssetService(client: MvpRequestClient(httpClient: mockHttp));
    final result = await service.publishAsset(
      assetKind: FounderAssetKind.skill,
      assetId: 'skill.custom.summary',
      version: '1',
      expectedHash: 'sha256:abc',
      reason: 'Đã evaluate PASS',
    );

    expect(result, isA<ApiSuccess<FounderAssetCommandResult>>());
    expect((result as ApiSuccess<FounderAssetCommandResult>).data.operation, 'PUBLISH');
  });

  test('surfaces a hash-conflict error without retrying silently', () async {
    final mockHttp = MockClient((request) async {
      return http.Response(
        jsonEncode({'message': 'expected_hash mismatch'}),
        409,
        headers: {'content-type': 'application/json'},
      );
    });

    final service = FounderAssetService(client: MvpRequestClient(httpClient: mockHttp));
    final result = await service.publishAsset(
      assetKind: FounderAssetKind.skill,
      assetId: 'skill.custom.summary',
      version: '1',
      expectedHash: 'sha256:stale',
      reason: 'Đã evaluate PASS',
    );

    expect(result, isA<ApiFailure<FounderAssetCommandResult>>());
    final failure = result as ApiFailure<FounderAssetCommandResult>;
    expect(failure.failure.statusCode, 409);
    expect(failure.failure.code, ApiFailureCode.conflict);
  });
}
