import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:frontend/core/network/api_client.dart';
import 'package:frontend/modules/onboarding/services/company_identity_service.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  SharedPreferences.setMockInitialValues({});

  late http.Client originalClient;
  setUp(() => originalClient = ApiClient.client);
  tearDown(() => ApiClient.client = originalClient);

  test('fetch returns a WorkspaceCompanyIdentity from GET /identity/workspaces/:id', () async {
    ApiClient.client = MockClient((request) async {
      expect(request.method, 'GET');
      expect(request.url.path, '/identity/workspaces/ws_1');
      return http.Response(
        '{"id":"ws_1","vision":"V","mission":"M","coreValues":"C"}',
        200,
      );
    });

    final result = await CompanyIdentityService().fetch('ws_1');
    expect(result.vision, 'V');
    expect(result.isComplete, isTrue);
  });

  test('fetch throws CompanyIdentityException on non-200', () async {
    ApiClient.client = MockClient((request) async {
      return http.Response('{"detail":"not found"}', 404);
    });

    expect(
      () => CompanyIdentityService().fetch('ws_missing'),
      throwsA(isA<CompanyIdentityException>()),
    );
  });

  test('save PATCHes company-identity with camelCase body and returns the updated model', () async {
    ApiClient.client = MockClient((request) async {
      expect(request.method, 'PATCH');
      expect(request.url.path, '/identity/workspaces/ws_1/company-identity');
      expect(
        request.body,
        '{"vision":"V","mission":"M","coreValues":"C"}',
      );
      return http.Response(
        '{"id":"ws_1","vision":"V","mission":"M","coreValues":"C"}',
        200,
      );
    });

    final result = await CompanyIdentityService().save(
      'ws_1',
      vision: 'V',
      mission: 'M',
      coreValues: 'C',
    );
    expect(result.isComplete, isTrue);
  });

  test('save throws CompanyIdentityException on non-200', () async {
    ApiClient.client = MockClient((request) async {
      return http.Response('{"detail":"vision, mission, and coreValues must all be non-empty"}', 400);
    });

    expect(
      () => CompanyIdentityService().save('ws_1', vision: '', mission: 'M', coreValues: 'C'),
      throwsA(isA<CompanyIdentityException>()),
    );
  });
}
