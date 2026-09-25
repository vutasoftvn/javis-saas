import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/modules/auth/services/core_auth_client.dart';
import 'package:frontend/modules/auth/services/core_profile_client.dart';
import 'package:frontend/modules/profile/controllers/profile_controller.dart';
import 'package:frontend/modules/auth/services/auth_service.dart';
import 'package:get/get.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

// Spec 2026-09-25 §8 — phone/tên hiển thị ghi thẳng vào API profile của Core
// bằng access token OIDC, không qua COSA `/platform/auth/me`.

http.Response _json(Object body, int status) =>
    http.Response(jsonEncode(body), status, headers: {'content-type': 'application/json'});

CoreProfileClient _client(MockClient mock, {String? token = 'core-token'}) => CoreProfileClient(
      client: mock,
      baseUrl: 'http://core.test/',
      accessToken: () async => token,
    );

class _NoMeAuthService extends AuthService {
  @override
  Future<Map<String, dynamic>?> getMe() async => {'id': 'u1', 'email': 'a@b.c', 'display_name': 'Old'};
}

void main() {
  group('CoreProfileClient', () {
    test('updateDisplayName calls PATCH /profile/display-name with the core bearer', () async {
      final client = _client(MockClient((request) async {
        expect(request.method, 'PATCH');
        expect(request.url.toString(), 'http://core.test/profile/display-name');
        expect(request.headers['Authorization'], 'Bearer core-token');
        expect(jsonDecode(request.body), {'displayName': 'Nguyen Van A'});
        return _json({'success': true, 'displayName': 'Nguyen Van A'}, 200);
      }));
      expect(await client.updateDisplayName('Nguyen Van A'), 'Nguyen Van A');
    });

    test('phone change is two-step: request OTP then verify', () async {
      final paths = <String>[];
      final client = _client(MockClient((request) async {
        paths.add(request.url.path);
        final body = jsonDecode(request.body) as Map<String, dynamic>;
        if (request.url.path == '/profile/phone/change') {
          expect(body, {'newPhone': '0912345678'});
          return _json({'message': 'OTP sent', 'phone': '+84912345678'}, 200);
        }
        expect(body, {'phone': '+84912345678', 'otp': '123456'});
        return _json({
          'message': 'ok',
          'profile': {'id': 'u1', 'phone': '+84912345678', 'kycLevel': 1, 'isActivePhone': true, 'isActiveEmail': true},
        }, 200);
      }));

      final challenge = await client.requestPhoneChange('0912345678');
      expect(challenge.phone, '+84912345678');
      expect(await client.verifyPhoneChange(phone: challenge.phone, otp: '123456'), '+84912345678');
      expect(paths, ['/profile/phone/change', '/profile/phone/verify']);
    });

    test('never calls COSA and surfaces core errors', () async {
      final client = _client(MockClient((request) async {
        expect(request.url.path.startsWith('/platform'), isFalse);
        return _json({'code': 'already_exists', 'message': 'Số điện thoại này đã được đăng ký'}, 409);
      }));
      await expectLater(
        client.requestPhoneChange('0912345678'),
        throwsA(isA<CoreAuthException>().having((e) => e.statusCode, 'status', 409)),
      );
    });

    test('fails closed without an access token', () async {
      final client = _client(MockClient((_) async => fail('must not call core')), token: null);
      await expectLater(
        client.updateDisplayName('X'),
        throwsA(isA<CoreAuthException>().having((e) => e.statusCode, 'status', 401)),
      );
    });
  });

  group('ProfileController phone flow', () {
    setUp(Get.reset);

    test('phone only changes after OTP is verified by core', () async {
      final controller = ProfileController(
        authService: _NoMeAuthService(),
        coreProfile: _client(MockClient((request) async {
          if (request.url.path == '/profile/phone/change') {
            return _json({'message': 'OTP sent', 'phone': '+84912345678'}, 200);
          }
          return _json({'message': 'ok', 'profile': {'phone': '+84912345678'}}, 200);
        })),
      );
      await controller.loadProfile();

      controller.phoneController.text = '0912345678';
      await controller.savePhone();
      expect(controller.pendingPhone.value, '+84912345678');
      expect(controller.phone.value, isNull);

      controller.otpController.text = '123456';
      await controller.verifyPhoneOtp();
      expect(controller.phone.value, '+84912345678');
      expect(controller.pendingPhone.value, isNull);
      expect(controller.errorMessage.value, isEmpty);
    });

    test('a core failure keeps the old display name and shows an error', () async {
      final controller = ProfileController(
        authService: _NoMeAuthService(),
        coreProfile: _client(MockClient((_) async => _json({'message': 'boom'}, 500))),
      );
      await controller.loadProfile();
      controller.displayNameController.text = 'New';
      await controller.saveDisplayName();
      expect(controller.displayName.value, 'Old');
      expect(controller.errorMessage.value, contains('boom'));
    });
  });
}
