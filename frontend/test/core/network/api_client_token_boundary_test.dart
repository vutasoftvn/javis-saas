// M1 §1 — ApiClient chọn token theo target đã resolve, không theo text path.
import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/core/network/api_client.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  late http.Client realClient;

  setUp(() {
    realClient = ApiClient.client;
    SharedPreferences.setMockInitialValues({
      'local_session_token': 'LOCAL_SESSION',
      'platform_access_token': 'PLATFORM_ACCESS',
      'workspace_id': '123',
    });
    ApiClient.setBaseUrl('http://company.local');
    ApiClient.setPlatformBaseUrl('http://platform.local');
    ApiClient.setAgentOsBaseUrl('http://agentos.local');
  });

  tearDown(() {
    ApiClient.client = realClient;
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

  test('AgentOS /agent endpoint carries the platform access token', () async {
    expect(await authHeaderFor('/agent/runs'), 'Bearer PLATFORM_ACCESS');
  });

  test('normalized legacy path (/auth -> /identity) still uses local session', () async {
    expect(await authHeaderFor('/auth/me'), 'Bearer LOCAL_SESSION');
  });

  test('falls back to legacy auth_token when split keys are absent', () async {
    SharedPreferences.setMockInitialValues({'auth_token': 'LEGACY_ONLY'});
    expect(await authHeaderFor('/operations/tasks'), 'Bearer LEGACY_ONLY');
    expect(await authHeaderFor('/platform/foo'), 'Bearer LEGACY_ONLY');
  });

  test('platform token expiry does not strand local calls (independent keys)', () async {
    SharedPreferences.setMockInitialValues({
      'local_session_token': 'LOCAL_SESSION',
      // no platform_access_token at all
    });
    expect(await authHeaderFor('/operations/tasks'), 'Bearer LOCAL_SESSION');
  });
}
