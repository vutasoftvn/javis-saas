// M1 §1 — ApiClient chọn token theo target đã resolve, không theo text path.
import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/core/network/api_client.dart';
import 'package:frontend/core/services/secure_storage_service.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../services/fakes/fake_secret_store.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  late http.Client realClient;

  // ApiAuthResolver đọc token qua SecureStorageService (secret store
  // fail-closed thật), không còn qua SharedPreferences trực tiếp — test
  // tiêm fake in-memory thay vì mock MethodChannel native.
  setUp(() async {
    realClient = ApiClient.client;
    SharedPreferences.setMockInitialValues({});
    SecureStorageService.configureForTest(FakeSecretStore());
    await SecureStorageService.write('local_session_token', 'LOCAL_SESSION');
    await SecureStorageService.write('platform_access_token', 'PLATFORM_ACCESS');
    await SecureStorageService.write('workspace_id', '123');
    ApiClient.setBaseUrl('http://company.local');
    ApiClient.setPlatformBaseUrl('http://platform.local');
    ApiClient.setAgentOsBaseUrl('http://agentos.local');
  });

  tearDown(() {
    ApiClient.client = realClient;
    SecureStorageService.resetForTest();
  });

  Future<String?> authHeaderFor(String endpoint) async {
    String? seen;
    ApiClient.client = MockClient((request) async {
      seen = request.headers['authorization'];
      return http.Response('{}', 200);
    });
    await ApiClient.get(endpoint);
    return seen;
  }

  test('company business endpoint carries the local session token', () async {
    expect(await authHeaderFor('/operations/tasks'), 'Bearer LOCAL_SESSION');
  });

  test('control-plane /platform endpoint carries the platform access token', () async {
    expect(await authHeaderFor('/platform/workspaces/1/entitlement'),
        'Bearer PLATFORM_ACCESS');
  });

  test('AgentOS /agent endpoint carries the local session token (local business runtime)', () async {
    expect(await authHeaderFor('/agent/runs'), 'Bearer LOCAL_SESSION');
  });

  test('normalized legacy path (/auth -> /identity) still uses local session', () async {
    expect(await authHeaderFor('/auth/me'), 'Bearer LOCAL_SESSION');
  });

  test('falls back to legacy auth_token when split keys are absent', () async {
    SecureStorageService.configureForTest(FakeSecretStore());
    await SecureStorageService.write('auth_token', 'LEGACY_ONLY');
    expect(await authHeaderFor('/operations/tasks'), 'Bearer LEGACY_ONLY');
    expect(await authHeaderFor('/platform/foo'), 'Bearer LEGACY_ONLY');
  });

  test('platform token expiry does not strand local calls (independent keys)', () async {
    SecureStorageService.configureForTest(FakeSecretStore());
    await SecureStorageService.write('local_session_token', 'LOCAL_SESSION');
    // no platform_access_token at all
    expect(await authHeaderFor('/operations/tasks'), 'Bearer LOCAL_SESSION');
  });
}
