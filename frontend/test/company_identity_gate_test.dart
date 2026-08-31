// frontend/test/company_identity_gate_test.dart
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:frontend/core/network/api_client.dart';
import 'package:frontend/modules/onboarding/services/company_identity_gate.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  SharedPreferences.setMockInitialValues({});

  late http.Client originalClient;
  setUp(() => originalClient = ApiClient.client);
  tearDown(() => ApiClient.client = originalClient);

  test('calls showModal when the workspace is missing vision/mission/coreValues', () async {
    ApiClient.client = MockClient((request) async {
      return http.Response('{"id":"ws_1","vision":null,"mission":null,"coreValues":null}', 200);
    });

    var shown = false;
    await CompanyIdentityGate.checkAndPrompt(
      'ws_1',
      showModal: (workspaceId) async {
        shown = true;
        expect(workspaceId, 'ws_1');
      },
    );

    expect(shown, isTrue);
  });

  test('does not call showModal when the workspace already has all three fields', () async {
    ApiClient.client = MockClient((request) async {
      return http.Response('{"id":"ws_1","vision":"V","mission":"M","coreValues":"C"}', 200);
    });

    var shown = false;
    await CompanyIdentityGate.checkAndPrompt(
      'ws_1',
      showModal: (workspaceId) async => shown = true,
    );

    expect(shown, isFalse);
  });

  test('fails open (does not call showModal) when the fetch itself errors', () async {
    ApiClient.client = MockClient((request) async {
      return http.Response('server error', 500);
    });

    var shown = false;
    await CompanyIdentityGate.checkAndPrompt(
      'ws_1',
      showModal: (workspaceId) async => shown = true,
    );

    expect(shown, isFalse);
  });
}
