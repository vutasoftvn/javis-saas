import 'dart:convert';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:frontend/core/network/api_result.dart';
import 'package:frontend/core/network/mvp_request_client.dart';
import 'package:frontend/core/services/secure_storage_service.dart';
import 'package:frontend/modules/settings/models/settings_models.dart';
import 'package:frontend/modules/settings/services/model_provider_service.dart';

http.Response _envelope(Object data) => http.Response(
      jsonEncode({
        'data': data,
        'meta': {
          'dataState': 'populated',
          'observedAt': '2026-09-26T00:00:00Z',
          'sources': [
            {'kind': 'agent_db', 'ref': 'models.model_provider_profiles'},
          ],
        },
      }),
      200,
      headers: {'content-type': 'application/json'},
    );

const _claudeProfile = {
  'profile_id': 'claude-code',
  'provider_type': 'claude_cli',
  'model_id': 'claude-code',
  'credential_configured': false,
  'allowed_model_ids': <String>[],
  'status': 'ACTIVE',
};

void main() {
  setUp(() async {
    SharedPreferences.setMockInitialValues({'workspace_id': '1001'});
    await SecureStorageService.write('auth_token', 'test-token');
  });

  test('listProviders gọi GET /agent/settings/model-providers thật', () async {
    final mockHttp = MockClient((request) async {
      expect(request.method, 'GET');
      expect(request.url.path, '/agent/settings/model-providers');
      return _envelope([_claudeProfile]);
    });
    final service = ModelProviderService(client: MvpRequestClient(httpClient: mockHttp));

    final result = await service.listProviders();

    expect(result, isA<ApiSuccess<List<ModelProviderModel>>>());
    final providers = (result as ApiSuccess<List<ModelProviderModel>>).data;
    expect(providers.single.providerType, 'claude_cli');
  });

  test('createProvider gửi body snake_case, bỏ field rỗng (CLI không cần api key)', () async {
    final mockHttp = MockClient((request) async {
      expect(request.method, 'POST');
      expect(request.url.path, '/agent/settings/model-providers');
      final body = jsonDecode(request.body) as Map<String, dynamic>;
      expect(body, {'provider_type': 'claude_cli', 'profile_id': 'claude-code'});
      return _envelope(_claudeProfile);
    });
    final service = ModelProviderService(client: MvpRequestClient(httpClient: mockHttp));

    final result = await service.createProvider(
      providerType: 'claude_cli',
      profileId: 'claude-code',
      apiKey: '',
      modelId: '  ',
    );

    expect(result, isA<ApiSuccess<ModelProviderModel>>());
  });

  test('testConnection và setPolicy dùng đúng path param', () async {
    final seen = <String>[];
    final mockHttp = MockClient((request) async {
      seen.add('${request.method} ${request.url.path}');
      if (request.url.path.endsWith('/test')) {
        return _envelope({
          'profile_id': 'claude-code',
          'provider_type': 'claude_cli',
          'model_id': 'claude-code',
          'ok': true,
          'live_call_attempted': true,
          'detail': 'live call thành công (CLI)',
        });
      }
      final body = jsonDecode(request.body) as Map<String, dynamic>;
      expect(body['primary_profile_id'], 'claude-code');
      return _envelope({
        'scope': 'WORKSPACE',
        'scope_key': '1001',
        'primary_profile_id': 'claude-code',
        'fallback_profile_ids': <String>[],
        'resolved_profile_id': 'claude-code',
        'resolved_provider_type': 'claude_cli',
        'resolved_model_id': 'claude-code',
        'is_system_default': false,
      });
    });
    final service = ModelProviderService(client: MvpRequestClient(httpClient: mockHttp));

    final test = await service.testConnection('claude-code');
    final policy = await service.setPolicy('_workspace_default', primaryProfileId: 'claude-code');

    expect((test as ApiSuccess<ModelProviderTestResultModel>).data.ok, isTrue);
    expect((policy as ApiSuccess<ModelPolicyModel>).data.resolvedProviderType, 'claude_cli');
    expect(seen, [
      'POST /agent/settings/model-providers/claude-code/test',
      'PUT /agent/settings/model-policies/_workspace_default',
    ]);
  });
}
