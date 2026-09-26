import 'dart:convert';

import 'package:crypto/crypto.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/modules/auth/services/core_auth_client.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

/// Server giả lập backend/core: /auth/signin -> /oauth/authorize (PKCE) -> /oauth/token.
class _FakeCore {
  final requests = <http.Request>[];
  String? challenge;
  String? code;
  int loginStatus = 200;
  int tokenStatus = 200;

  /// Bước 2FA core đòi sau mật khẩu; rỗng = đăng nhập xong ngay bằng mật khẩu.
  List<String> signinSteps = const [];
  String? verifiedCode = '123456';

  MockClient get client => MockClient((request) async {
        requests.add(request);
        final path = request.url.path;
        if (path == '/auth/signin') {
          if (loginStatus != 200) return http.Response('{}', loginStatus);
          return http.Response(
            jsonEncode({
              'sessionId': '1',
              'userId': '42',
              'steps': signinSteps,
              if (signinSteps.isEmpty)
                'tokens': {'accessToken': 'session-jwt', 'refreshToken': 'session-refresh', 'expiresIn': 3600},
            }),
            200,
          );
        }
        if (path == '/auth/signin/1/otp') {
          return http.Response(jsonEncode({'code': '', 'sessionId': '1', 'step': 'otp_email'}), 200);
        }
        if (path == '/auth/signin/step') {
          final body = jsonDecode(request.body) as Map<String, dynamic>;
          if (body['code'] != verifiedCode) {
            return http.Response(
              jsonEncode({'message': 'Mã OTP không đúng'}),
              401,
              headers: {'content-type': 'application/json; charset=utf-8'},
            );
          }
          return http.Response(
            jsonEncode({
              'completed': [body['step']],
              'remaining': <String>[],
              'done': true,
              'accessToken': 'session-jwt',
              'refreshToken': 'session-refresh',
              'expiresIn': 3600,
            }),
            200,
          );
        }
        if (path == '/auth/signup/complete') {
          if (loginStatus != 200) return http.Response('{}', loginStatus);
          return http.Response(
            jsonEncode({
              'user': {'id': '42', 'email': 'a@b.vn', 'displayName': 'An'},
              'accessToken': 'session-jwt',
              'refreshToken': 'session-refresh',
              'expiresIn': 3600,
            }),
            200,
          );
        }
        if (path == '/auth/signup') {
          return http.Response(jsonEncode({'success': true, 'message': 'OTP sent'}), 200);
        }
        if (path == '/oauth/authorize') {
          expect(request.headers['Authorization'], 'Bearer session-jwt');
          challenge = request.url.queryParameters['code_challenge'];
          code = 'auth-code-1';
          return http.Response(
            jsonEncode({
              'redirectUrl':
                  '${request.url.queryParameters['redirect_uri']}?code=$code&state=${request.url.queryParameters['state']}',
            }),
            200,
          );
        }
        if (path == '/oauth/token') {
          if (tokenStatus != 200) return http.Response('{}', tokenStatus);
          final body = jsonDecode(request.body) as Map<String, dynamic>;
          if (body['grant_type'] == 'refresh_token') {
            return http.Response(
              jsonEncode({'access_token': 'refreshed', 'refresh_token': 'r2', 'expires_in': 3600}),
              200,
            );
          }
          // PKCE: sha256(verifier) phải khớp challenge đã gửi lúc authorize.
          final digest = sha256.convert(utf8.encode(body['code_verifier'] as String));
          expect(base64Url.encode(digest.bytes).replaceAll('=', ''), challenge);
          expect(body['code'], code);
          return http.Response(
            jsonEncode({
              'access_token': 'opaque-access',
              'refresh_token': 'oidc-refresh',
              'expires_in': 3600,
              'token_type': 'Bearer',
            }),
            200,
          );
        }
        return http.Response('not found', 404);
      });
}

void main() {
  group('CoreAuthClient', () {
    late _FakeCore core;
    late CoreAuthClient auth;

    setUp(() {
      core = _FakeCore();
      auth = CoreAuthClient(client: core.client, baseUrl: 'http://core.test');
    });

    test('login: /auth/signin rồi đổi phiên lấy access token OIDC của vn.mivacorp.cosa bằng PKCE', () async {
      final session = await auth.login('a@b.vn', 'secret-pw');

      expect(session.accessToken, 'opaque-access');
      expect(session.refreshToken, 'oidc-refresh');
      expect(session.user['id'], '42');

      final login = core.requests.firstWhere((r) => r.url.path == '/auth/signin');
      expect(login.headers['X-Client-ID'], 'vn.mivacorp.cosa');
      final loginBody = jsonDecode(login.body) as Map<String, dynamic>;
      expect(loginBody['email'], 'a@b.vn');
      expect(loginBody['password'], 'secret-pw');
      expect(loginBody['clientId'], 'vn.mivacorp.cosa');

      final authorize = core.requests.firstWhere((r) => r.url.path == '/oauth/authorize');
      expect(authorize.url.queryParameters['client_id'], 'vn.mivacorp.cosa');
      expect(authorize.url.queryParameters['code_challenge_method'], 'S256');
      expect(authorize.url.queryParameters['scope'], 'openid profile email offline_access');

      final token = core.requests.firstWhere((r) => r.url.path == '/oauth/token');
      final tokenBody = jsonDecode(token.body) as Map<String, dynamic>;
      expect(tokenBody['client_id'], 'vn.mivacorp.cosa');
      expect(tokenBody['redirect_uri'], authorize.url.queryParameters['redirect_uri']);
      // Client public: không bao giờ gửi client_secret.
      expect(tokenBody.containsKey('client_secret'), isFalse);
    });

    test('login: core đòi pin_local|otp_email|passkey_2fa -> chọn otp_email, không phải lỗi 412 cứng', () async {
      core.signinSteps = ['pin_local', 'otp_email', 'passkey_2fa'];

      final challenge = await auth
          .login('a@b.vn', 'pw')
          .then<CoreSecondFactorRequired?>((_) => null)
          .onError<CoreSecondFactorRequired>((e, _) => e);

      expect(challenge, isNotNull);
      expect(challenge!.step, 'otp_email');
      expect(challenge.sessionId, '1');
      expect(challenge.needsOtpRequest, isTrue);
      // Chưa đổi phiên OIDC khi 2FA còn dang dở.
      expect(core.requests.any((r) => r.url.path == '/oauth/token'), isFalse);
    });

    test('login: chỉ có bước web không làm được (pin_local) -> CoreAuthException(412)', () async {
      core.signinSteps = ['pin_local', 'passkey_2fa'];
      await expectLater(
        auth.login('a@b.vn', 'pw'),
        throwsA(
          isA<CoreAuthException>()
              .having((e) => e, 'không phải CoreSecondFactorRequired', isNot(isA<CoreSecondFactorRequired>()))
              .having((e) => e.statusCode, 'statusCode', 412),
        ),
      );
    });

    test('2FA otp_email: yêu cầu OTP, xác minh bước rồi đổi lấy access token OIDC', () async {
      core.signinSteps = ['pin_local', 'otp_email', 'passkey_2fa'];
      late CoreSecondFactorRequired challenge;
      try {
        await auth.login('a@b.vn', 'pw');
        fail('phải đòi 2FA');
      } on CoreSecondFactorRequired catch (e) {
        challenge = e;
      }

      await auth.requestSigninOtp(challenge);
      final otpReq = core.requests.firstWhere((r) => r.url.path == '/auth/signin/1/otp');
      expect(otpReq.url.queryParameters['step'], 'otp_email');

      final session = await auth.verifySigninStep(challenge, '123456');
      expect(session.accessToken, 'opaque-access');
      expect(session.user['id'], '42');

      final stepReq = core.requests.firstWhere((r) => r.url.path == '/auth/signin/step');
      final body = jsonDecode(stepReq.body) as Map<String, dynamic>;
      expect(body['sessionId'], '1');
      expect(body['step'], 'otp_email');
      expect(body['code'], '123456');
      // deviceId phải trùng với deviceId lúc initiate.
      final loginBody = jsonDecode(core.requests.firstWhere((r) => r.url.path == '/auth/signin').body) as Map;
      expect(body['deviceId'], loginBody['deviceId']);
    });

    test('2FA: mã sai -> CoreAuthException(401) mang thông báo của core', () async {
      core.signinSteps = ['otp_email'];
      late CoreSecondFactorRequired challenge;
      try {
        await auth.login('a@b.vn', 'pw');
      } on CoreSecondFactorRequired catch (e) {
        challenge = e;
      }
      await expectLater(
        auth.verifySigninStep(challenge, '000000'),
        throwsA(isA<CoreAuthException>().having((e) => e.statusCode, 'statusCode', 401)),
      );
    });

    test('login: 401 từ core -> CoreAuthException(401)', () async {
      core.loginStatus = 401;
      await expectLater(
        auth.login('a@b.vn', 'wrong'),
        throwsA(isA<CoreAuthException>().having((e) => e.statusCode, 'statusCode', 401)),
      );
    });

    test('login: core từ chối đổi token -> CoreAuthException', () async {
      core.tokenStatus = 400;
      await expectLater(auth.login('a@b.vn', 'pw'), throwsA(isA<CoreAuthException>()));
    });

    test('mỗi lần login dùng code_verifier khác nhau', () async {
      await auth.login('a@b.vn', 'pw');
      final first = core.challenge;
      await auth.login('a@b.vn', 'pw');
      expect(core.challenge, isNot(first));
    });

    test('requestSignupOtp gửi email, tên hiển thị và client id', () async {
      await auth.requestSignupOtp(email: 'a@b.vn', displayName: 'An');

      final req = core.requests.firstWhere((r) => r.url.path == '/auth/signup');
      expect(req.headers['X-Client-ID'], 'vn.mivacorp.cosa');
      final body = jsonDecode(req.body) as Map<String, dynamic>;
      expect(body['email'], 'a@b.vn');
      expect(body['displayName'], 'An');
    });

    test('completeSignup: hoàn tất đăng ký rồi đổi lấy access token', () async {
      final session = await auth.completeSignup(
        email: 'a@b.vn',
        password: 'secret-pw',
        otp: '123456',
        displayName: 'An',
        preferredLanguage: 'vi',
      );

      expect(session.accessToken, 'opaque-access');
      final req = core.requests.firstWhere((r) => r.url.path == '/auth/signup/complete');
      final body = jsonDecode(req.body) as Map<String, dynamic>;
      expect(body['emailOrPhone'], 'a@b.vn');
      expect(body['otp'], '123456');
      expect(body['password'], 'secret-pw');
      expect(body['preferredLanguage'], 'vi');
    });

    test('refresh: đổi refresh token lấy access token mới', () async {
      final session = await auth.refresh('oidc-refresh');

      expect(session.accessToken, 'refreshed');
      expect(session.refreshToken, 'r2');
      final token = core.requests.firstWhere((r) => r.url.path == '/oauth/token');
      final body = jsonDecode(token.body) as Map<String, dynamic>;
      expect(body['grant_type'], 'refresh_token');
      expect(body['refresh_token'], 'oidc-refresh');
      expect(body['client_id'], 'vn.mivacorp.cosa');
    });
  });
}
