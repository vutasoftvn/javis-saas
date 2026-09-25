import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/core/network/api_client.dart';
import 'package:frontend/core/services/secure_storage_service.dart';
import 'package:frontend/modules/auth/services/auth_service.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';

// Spec 2026-09-25 §8 — đổi locale chỉ đi qua route preference của COSA và
// không mang dữ liệu liên hệ thuộc Core.
void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  late http.Client realClient;

  setUp(() async {
    realClient = ApiClient.client;
    SharedPreferences.setMockInitialValues({});
    await SecureStorageService.write('auth_token', 'token');
  });

  tearDown(() => ApiClient.client = realClient);

  test('updatePreferences patches /platform/preferences/me with locale only', () async {
    ApiClient.client = MockClient((request) async {
      expect(request.method, 'PATCH');
      expect(request.url.path, '/platform/preferences/me');
      expect(jsonDecode(request.body), {'preferredLocale': 'en-US'});
      return http.Response(jsonEncode({'preferred_locale': 'en-US'}), 200);
    });

    final result = await AuthService().updatePreferences(preferredLocale: 'en-US');

    expect(result?['preferred_locale'], 'en-US');
  });

  test('updatePreferences returns null on a rejected update', () async {
    ApiClient.client = MockClient((request) async => http.Response('{"code":"invalid_argument"}', 400));
    expect(await AuthService().updatePreferences(preferredLocale: 'fr-FR'), isNull);
  });
}
