import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/core/network/api_client.dart';
import 'package:frontend/core/services/secure_storage_service.dart';
import 'package:frontend/modules/auth/controllers/auth_controller.dart';
import 'package:frontend/modules/auth/services/auth_service.dart';
import 'package:get/get.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../../core/services/fakes/fake_secret_store.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  Get.testMode = true;

  late List<String> calls;
  late int signupStatus;

  setUp(() {
    SharedPreferences.setMockInitialValues({});
    SecureStorageService.configureForTest(FakeSecretStore());
    calls = [];
    signupStatus = 200;
    ApiClient.client = MockClient((request) async {
      calls.add(request.url.path);
      switch (request.url.path) {
        case '/auth/signup':
          if (signupStatus != 200) return http.Response('{}', signupStatus);
          return http.Response('{"success":true,"message":"OTP sent"}', 200);
        case '/auth/signup/complete':
          expect((jsonDecode(request.body) as Map)['otp'], '654321');
          return http.Response(
            '{"user":{"id":"7"},"accessToken":"session-jwt","refreshToken":"r0","expiresIn":3600}',
            200,
          );
        case '/oauth/authorize':
          final q = request.url.queryParameters;
          return http.Response('{"redirectUrl":"${q['redirect_uri']}?code=c1&state=${q['state']}"}', 200);
        case '/oauth/token':
          return http.Response(
            '{"access_token":"core-access","refresh_token":"oidc-r","expires_in":3600}',
            200,
          );
      }
      return http.Response('{}', 404);
    });
  });

  tearDown(() {
    ApiClient.client = http.Client();
    SecureStorageService.resetForTest();
    AuthService.setCachedToken(null);
  });

  AuthController filledController() {
    final c = AuthController();
    c.regDisplayNameController.text = 'An Nguyen';
    c.regEmailController.text = 'an@example.com';
    c.regPasswordController.text = 'secretpw1';
    c.regConfirmPasswordController.text = 'secretpw1';
    return c;
  }

  test('lần bấm đầu chỉ gửi OTP và giữ nguyên bước, chưa tạo tài khoản', () async {
    final c = filledController();

    await c.submitAccountStep();

    expect(calls, ['/auth/signup']);
    expect(c.otpRequested.value, isTrue);
    expect(c.registerStep.value, 1);
    expect(c.registerErrorMessage.value, isEmpty);
  });

  test('lần bấm sau cần mã OTP; có mã thì hoàn tất tài khoản và sang bước công ty', () async {
    final c = filledController();
    await c.submitAccountStep();

    // Thiếu mã: không gọi core.
    await c.submitAccountStep();
    expect(c.registerErrorMessage.value, contains('mã xác nhận'));
    expect(calls, ['/auth/signup']);

    c.regOtpController.text = '654321';
    await c.submitAccountStep();

    expect(calls, contains('/auth/signup/complete'));
    expect(c.registeredPlatformToken.value, 'core-access');
    expect(c.registerStep.value, 2);
  });

  test('gửi OTP thất bại (email đã đăng ký): báo lỗi và không chuyển pha', () async {
    signupStatus = 409;
    final c = filledController();

    await c.submitAccountStep();

    expect(c.otpRequested.value, isFalse);
    expect(c.registerErrorMessage.value, contains('đã được đăng ký'));
  });

  test('editAccountDetails quay về pha nhập thông tin và xoá mã cũ', () async {
    final c = filledController();
    await c.submitAccountStep();
    c.regOtpController.text = '111111';

    c.editAccountDetails();

    expect(c.otpRequested.value, isFalse);
    expect(c.regOtpController.text, isEmpty);
  });
}
