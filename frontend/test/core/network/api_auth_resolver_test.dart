import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:frontend/core/network/api_auth_resolver.dart';
import 'package:frontend/core/network/api_result.dart';
import 'package:frontend/core/services/secure_storage_service.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() async {
    SharedPreferences.setMockInitialValues({});
  });

  group('ApiAuthResolver', () {
    const resolver = DefaultApiAuthResolver();

    test('Platform plane resolves only platform_access_token or legacy fallback', () async {
      await SecureStorageService.write('platform_access_token', 'token_platform_123');
      await SecureStorageService.write('local_session_token', 'token_company_456');

      final token = await resolver.tokenFor(ApiPlane.platform);
      expect(token, equals('token_platform_123'));
    });

    test('Company plane resolves only local_session_token or legacy fallback', () async {
      await SecureStorageService.write('platform_access_token', 'token_platform_123');
      await SecureStorageService.write('local_session_token', 'token_company_456');

      final token = await resolver.tokenFor(ApiPlane.company);
      expect(token, equals('token_company_456'));
    });

    test('Agent plane resolves local_session_token or legacy fallback', () async {
      await SecureStorageService.write('local_session_token', 'token_agent_789');

      final token = await resolver.tokenFor(ApiPlane.agent);
      expect(token, equals('token_agent_789'));
    });

    test('Missing token does not cross-pollinate to another plane', () async {
      await SecureStorageService.write('platform_access_token', 'token_platform_only');

      // Company plane has no local_session_token or auth_token
      final companyToken = await resolver.tokenFor(ApiPlane.company);
      expect(companyToken, isNull);
    });

    test('Legacy auth_token acts as backward-compatible fallback for all planes', () async {
      await SecureStorageService.write('auth_token', 'legacy_token_abc');

      expect(await resolver.tokenFor(ApiPlane.platform), equals('legacy_token_abc'));
      expect(await resolver.tokenFor(ApiPlane.company), equals('legacy_token_abc'));
      expect(await resolver.tokenFor(ApiPlane.agent), equals('legacy_token_abc'));
    });

    test('Workspace ID is resolved unchanged from secure storage', () async {
      await SecureStorageService.write('workspace_id', 'ws_enterprise_999');

      final wsId = await resolver.workspaceId();
      expect(wsId, equals('ws_enterprise_999'));
    });
  });
}
