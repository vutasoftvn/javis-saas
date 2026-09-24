import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/core/network/platform_token_provider.dart';
import 'package:frontend/core/services/secure_storage_service.dart';
import 'package:frontend/modules/auth/services/core_auth_client.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../services/fakes/fake_secret_store.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  late int refreshCalls;
  late int refreshStatus;

  CoreAuthClient fakeCore() => CoreAuthClient(
        baseUrl: 'http://core.test',
        client: MockClient((request) async {
          if (request.url.path == '/oauth/token') {
            refreshCalls++;
            if (refreshStatus != 200) return http.Response('{}', refreshStatus);
            final body = jsonDecode(request.body) as Map<String, dynamic>;
            expect(body['grant_type'], 'refresh_token');
            expect(body['refresh_token'], 'refresh-1');
            return http.Response(
              jsonEncode({'access_token': 'fresh-access', 'refresh_token': 'refresh-2', 'expires_in': 3600}),
              200,
            );
          }
          return http.Response('{}', 404);
        }),
      );

  setUp(() {
    SharedPreferences.setMockInitialValues({});
    SecureStorageService.configureForTest(FakeSecretStore());
    refreshCalls = 0;
    refreshStatus = 200;
    PlatformTokenProvider.configureForTest(coreAuth: fakeCore(), now: () => DateTime.utc(2026, 9, 24, 10));
  });

  tearDown(() {
    PlatformTokenProvider.resetForTest();
    SecureStorageService.resetForTest();
  });

  test('token còn hạn: trả nguyên, không gọi core', () async {
    await PlatformTokenProvider.saveSession(
      const CoreSession(accessToken: 'access-1', refreshToken: 'refresh-1', expiresIn: 3600),
    );

    expect(await PlatformTokenProvider.currentToken(), 'access-1');
    expect(refreshCalls, 0);
  });

  test('token sắp hết hạn (< 60 giây): làm mới bằng refresh token và lưu phiên mới', () async {
    await PlatformTokenProvider.saveSession(
      const CoreSession(accessToken: 'access-1', refreshToken: 'refresh-1', expiresIn: 30),
    );

    expect(await PlatformTokenProvider.currentToken(), 'fresh-access');
    expect(refreshCalls, 1);
    expect(await SecureStorageService.read('platform_access_token'), 'fresh-access');
    expect(await SecureStorageService.read('core_refresh_token'), 'refresh-2');
    // Lần sau đã còn hạn, không làm mới nữa.
    expect(await PlatformTokenProvider.currentToken(), 'fresh-access');
    expect(refreshCalls, 1);
  });

  test('nhiều request đồng thời chỉ làm mới một lần', () async {
    await PlatformTokenProvider.saveSession(
      const CoreSession(accessToken: 'access-1', refreshToken: 'refresh-1', expiresIn: 5),
    );

    final results = await Future.wait([
      PlatformTokenProvider.currentToken(),
      PlatformTokenProvider.currentToken(),
      PlatformTokenProvider.currentToken(),
    ]);

    expect(results, everyElement('fresh-access'));
    expect(refreshCalls, 1);
  });

  test('làm mới thất bại: vẫn trả token hiện có để server quyết định (không nuốt thành null)', () async {
    refreshStatus = 400;
    await PlatformTokenProvider.saveSession(
      const CoreSession(accessToken: 'access-1', refreshToken: 'refresh-1', expiresIn: 5),
    );

    expect(await PlatformTokenProvider.currentToken(), 'access-1');
  });

  test('phiên cũ không có thông tin hết hạn hoặc refresh token: trả nguyên token', () async {
    await SecureStorageService.write('platform_access_token', 'legacy-platform-jwt');

    expect(await PlatformTokenProvider.currentToken(), 'legacy-platform-jwt');
    expect(refreshCalls, 0);
  });

  test('không có token nào: trả null', () async {
    expect(await PlatformTokenProvider.currentToken(), isNull);
  });

  test('clear xoá token, refresh token và hạn dùng', () async {
    await PlatformTokenProvider.saveSession(
      const CoreSession(accessToken: 'access-1', refreshToken: 'refresh-1', expiresIn: 3600),
    );

    await PlatformTokenProvider.clear();

    expect(await SecureStorageService.read('platform_access_token'), isNull);
    expect(await SecureStorageService.read('core_refresh_token'), isNull);
    expect(await SecureStorageService.read('platform_access_expires_at'), isNull);
  });
}
