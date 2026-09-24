import 'dart:convert';
import 'dart:io';
import 'package:flutter_test/flutter_test.dart';
import 'package:get/get.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:frontend/core/network/api_client.dart';
import 'package:frontend/core/services/secure_storage_service.dart';
import 'package:frontend/modules/auth/services/auth_service.dart';
import 'package:frontend/core/routing/auth_middleware.dart';
import 'package:frontend/core/routing/app_routes.dart';
import 'package:frontend/modules/auth/controllers/auth_controller.dart';

import 'core/services/fakes/fake_secret_store.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  Get.testMode = true;

  // Token (auth_token/local_session_token/platform_access_token) đi qua
  // secret store fail-closed thật (Keychain/Keystore) chứ không còn qua
  // SharedPreferences — widget test tiêm fake in-memory thay vì mock
  // MethodChannel để không phải quan tâm platform channel native.
  setUp(() {
    SharedPreferences.setMockInitialValues({});
    SecureStorageService.configureForTest(FakeSecretStore());
  });

  tearDown(() {
    SecureStorageService.resetForTest();
    // `AuthService._cachedToken` là static singleton: một test set token
    // (vd. group "State & Tokens") mà không dọn sẽ khiến test sau thấy
    // `AuthService.isAuthenticated == true` sai lệch. Ở thứ tự khai báo, test
    // `logout` tình cờ chạy cuối group nên che được rò rỉ này; random order /
    // full-suite thì không. Reset global để mọi test bắt đầu từ trạng thái sạch.
    AuthService.setCachedToken(null);
  });

  group('AuthService State & Tokens', () {
    test('isAuthenticated is false when no token is present', () async {
      AuthService.setCachedToken(null);
      expect(AuthService.isAuthenticated, isFalse);
    });

    test('isAuthenticated is true when token is set', () async {
      AuthService.setCachedToken('mock-jwt-token-xyz');
      expect(AuthService.isAuthenticated, isTrue);
    });

    test('init loads saved auth_token from SharedPreferences', () async {
      SharedPreferences.setMockInitialValues({
        'auth_token': 'saved-token-123',
      });
      await AuthService.init();
      expect(AuthService.isAuthenticated, isTrue);
    });

    test('logout clears cached token and storage', () async {
      SharedPreferences.setMockInitialValues({
        'auth_token': 'saved-token-123',
        'workspace_id': 'ws-123',
      });
      await AuthService.init();
      expect(AuthService.isAuthenticated, isTrue);

      final service = AuthService();
      await service.logout();

      expect(AuthService.isAuthenticated, isFalse);
      final prefs = await SharedPreferences.getInstance();
      expect(prefs.getString('auth_token'), isNull);
      expect(prefs.getString('workspace_id'), isNull);
    });
  });

  group('AuthService Platform-First Flow', () {
    tearDown(() {
      ApiClient.client = http.Client();
      AuthService.setCachedToken(null);
    });

    /// Backend/core giả lập cho luồng đăng nhập first-party: /auth/login -> /oauth/authorize -> /oauth/token.
    Future<http.Response> coreHandler(http.Request request, int loginStatus, int signupCompleteStatus) async {
      switch (request.url.path) {
        case '/auth/login':
          if (loginStatus != 200) return http.Response('{}', loginStatus);
          return http.Response(
            '{"user":{"id":"42","email":"founder@cosa.dev"},"accessToken":"session-jwt","refreshToken":"r0","expiresIn":3600}',
            200,
          );
        case '/auth/signup':
          return http.Response('{"success":true,"message":"OTP sent"}', 200);
        case '/auth/signup/complete':
          if (signupCompleteStatus != 200) return http.Response('{}', signupCompleteStatus);
          return http.Response(
            '{"user":{"id":"43","email":"new@cosa.dev"},"accessToken":"session-jwt","refreshToken":"r0","expiresIn":3600}',
            200,
          );
        case '/oauth/authorize':
          final q = request.url.queryParameters;
          return http.Response('{"redirectUrl":"${q['redirect_uri']}?code=c1&state=${q['state']}"}', 200);
        case '/oauth/token':
          return http.Response(
            '{"access_token":"plat-tok-123","refresh_token":"oidc-r","expires_in":3600,"token_type":"Bearer"}',
            200,
          );
      }
      return http.Response('not found', 404);
    }

    MockClient fakeCoreLogin({int loginStatus = 200, int signupCompleteStatus = 200}) {
      return MockClient((request) => coreHandler(request, loginStatus, signupCompleteStatus));
    }

    test('loginPlatform returns the core OIDC access token (does not cache it as auth_token)', () async {
      ApiClient.client = fakeCoreLogin();

      final service = AuthService();
      final result = await service.loginPlatform('founder@cosa.dev', 'pw');

      expect(result.success, isTrue);
      expect(result.token, 'plat-tok-123');
      expect(result.user?['id'], '42');
      // Token core được lưu làm platform_access_token kèm refresh token để tự làm mới.
      expect(await SecureStorageService.read('platform_access_token'), 'plat-tok-123');
      expect(await SecureStorageService.read('core_refresh_token'), 'oidc-r');
      expect(AuthService.isAuthenticated, isFalse); // chua sync-from-platform nen chua co auth_token local
    });

    test('loginPlatform surfaces 401 as a friendly error', () async {
      ApiClient.client = fakeCoreLogin(loginStatus: 401);

      final service = AuthService();
      final result = await service.loginPlatform('founder@cosa.dev', 'wrong');

      expect(result.success, isFalse);
      expect(result.errorMessage, contains('không chính xác'));
    });

    test('syncFromPlatform does NOT send company_id and returns parsed workspaces list', () async {
      ApiClient.client = MockClient((request) async {
        // Verify no company_id in request body
        expect(request.url.path, contains('/identity/sync-from-platform'));
        final body = request.body;
        expect(body, isNotEmpty);
        expect(body, isNot(contains('company_id')));
        // M2 §29 (P0) — client KHÔNG BAO GIỜ được gửi `user`/`workspaces` lên
        // sync-from-platform nữa: server luôn tự lấy/xác thực membership từ
        // Control Plane, không tin bất kỳ payload nào client tự khai (chặn
        // leo thang đặc quyền qua role_id tự gửi).
        final decoded = jsonDecode(body) as Map<String, dynamic>;
        expect(decoded.containsKey('workspaces'), isFalse);
        expect(decoded.containsKey('user'), isFalse);
        expect(decoded.keys.toSet(), {'platform_access_token'});
        // Verify no X-Company-Id header
        expect(request.headers.containsKey('X-Company-Id'), isFalse);
        return http.Response(
          '{"access_token":"local-jwt-123","token_type":"bearer","workspaces":[{"workspaceId":"real-ws-1","name":"Workspace A","role":"founder","status":"active"},{"workspaceId":"real-ws-2","name":"Workspace B","role":"member","status":"active"}]}',
          200,
        );
      });

      final service = AuthService();
      final result = await service.syncFromPlatform(platformToken: 'plat-tok-123');

      expect(result.success, isTrue);
      expect(result.token, 'local-jwt-123');

      // CRITICAL: Verify workspaces are parsed from backend response
      expect(result.workspaces, isNotNull);
      expect(result.workspaces!.length, 2);
      expect(result.workspaces![0].workspaceId, 'real-ws-1'); // Real local workspace ID
      expect(result.workspaces![0].name, 'Workspace A');
      expect(result.workspaces![0].roleId, 'founder');
      expect(result.workspaces![1].workspaceId, 'real-ws-2');

      // Token is cached trong secret store (không phải SharedPreferences);
      // company_id không bao giờ xuất hiện ở đâu cả.
      expect(AuthService.isAuthenticated, isTrue);
      expect(await SecureStorageService.read('auth_token'), 'local-jwt-123');
      final prefs = await SharedPreferences.getInstance();
      expect(prefs.getString('company_id'), isNull);
    });

    test('requestSignupOtp asks core to send an OTP to the email', () async {
      final seen = <String>[];
      ApiClient.client = MockClient((request) async {
        seen.add(request.url.path);
        final decoded = jsonDecode(request.body) as Map<String, dynamic>;
        expect(decoded['email'], 'new@cosa.dev');
        return http.Response('{"success":true,"message":"OTP sent"}', 200);
      });

      final result = await AuthService().requestSignupOtp(email: 'new@cosa.dev', displayName: 'New');

      expect(result.success, isTrue);
      expect(seen, ['/auth/signup']);
    });

    test('registerPlatform completes signup with the OTP and returns the core access token', () async {
      final signupBodies = <Map<String, dynamic>>[];
      ApiClient.client = MockClient((request) {
        if (request.url.path == '/auth/signup/complete') {
          signupBodies.add(jsonDecode(request.body) as Map<String, dynamic>);
        }
        return coreHandler(request, 200, 200);
      });

      final service = AuthService();
      final result = await service.registerPlatform(
        email: 'new@cosa.dev',
        password: 'secretpw',
        displayName: 'New',
        otp: '123456',
        preferredLocale: 'vi-VN',
      );

      expect(result.success, isTrue);
      expect(result.token, 'plat-tok-123');
      expect(signupBodies.single['otp'], '123456');
      expect(signupBodies.single['preferredLanguage'], 'vi');
      expect(await SecureStorageService.read('platform_access_token'), 'plat-tok-123');
    });

    test('registerPlatform surfaces a wrong OTP as a friendly error', () async {
      ApiClient.client = fakeCoreLogin(signupCompleteStatus: 401);

      final result = await AuthService().registerPlatform(
        email: 'new@cosa.dev',
        password: 'secretpw',
        displayName: 'New',
        otp: '000000',
      );

      expect(result.success, isFalse);
      expect(result.errorMessage, contains('Mã xác nhận'));
    });

    test('registerPlatform surfaces 409 as email-taken error', () async {
      ApiClient.client = fakeCoreLogin(signupCompleteStatus: 409);

      final service = AuthService();
      final result = await service.registerPlatform(
        email: 'founder@cosa.dev',
        password: 'secretpw',
        displayName: 'Founder',
        otp: '123456',
      );

      expect(result.success, isFalse);
      expect(result.errorMessage, contains('đã được đăng ký'));
    });

    test('createCompany creates new company and returns companyId', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.url.path, contains('/platform/auth/companies/create'));
        expect(request.headers['Authorization'], 'Bearer plat-tok-123');
        return http.Response(
          '{"company_id":"888","name":"New Company","role_id":"founder"}',
          200,
        );
      });

      final service = AuthService();
      final result = await service.createCompany(platformToken: 'plat-tok-123', companyName: 'New Company');

      expect(result.success, isTrue);
      expect(result.companyId, '888');
    });

    test('acceptWorkspaceInvitation posts opaque token to the invitations/accept route and returns companyId', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.url.path, contains('/platform/auth/companies/invitations/accept'));
        expect(request.headers['Authorization'], 'Bearer plat-tok-123');
        final decoded = jsonDecode(request.body) as Map<String, dynamic>;
        // Token là chuỗi opaque base64url — request body chỉ có `token`,
        // KHÔNG BAO GIỜ `company_id` (đó là route join-by-id đã bị gỡ).
        expect(decoded.keys.toSet(), {'token'});
        expect(decoded['token'], 'inv-tok_ABC123-xyz');
        return http.Response(
          '{"company_id":"999","name":"Joined Co","role_id":"member"}',
          200,
        );
      });

      final service = AuthService();
      final result = await service.acceptWorkspaceInvitation(
        platformToken: 'plat-tok-123',
        invitationToken: 'inv-tok_ABC123-xyz',
      );

      expect(result.success, isTrue);
      expect(result.companyId, '999');
    });

    // Task 6 — chốt Snowflake ID (`company_id` trả về từ accept) không bao giờ
    // đi qua `int`/`double` ở bất kỳ điểm nào trong AuthService. ID biên
    // 9223372036854775807 (2^63-1) vượt Number.MAX_SAFE_INTEGER của Dart/JS
    // (2^53-1) — nếu code có `int.tryParse`/ép kiểu số ở đâu đó, giá trị exact
    // này sẽ bị làm tròn hoặc mất, không round-trip nguyên vẹn.
    test('acceptWorkspaceInvitation round-trips a full 19-digit Snowflake company_id as an exact String, never a num', () async {
      const snowflakeId = '9223372036854775807';
      ApiClient.client = MockClient((request) async {
        return http.Response(
          '{"company_id":"$snowflakeId","name":"Precision Co","role_id":"member","workspace":{"workspace_id":"$snowflakeId","workspace_name":"Precision Co","role_id":"member","status":"active"}}',
          200,
        );
      });

      final service = AuthService();
      final result = await service.acceptWorkspaceInvitation(
        platformToken: 'plat-tok-123',
        invitationToken: 'inv-tok-precision',
      );

      expect(result.success, isTrue);
      expect(result.companyId, isA<String>());
      expect(result.companyId, snowflakeId);
      expect(result.rawWorkspaces, isNotNull);
      expect(result.rawWorkspaces!.first['workspace_id'], snowflakeId);
    });

    test('syncFromPlatform stores the returned token as the local auth_token', () async {
      ApiClient.client = MockClient((request) async {
        expect(
          request.url.path,
          anyOf(contains('/auth/sync-from-platform'), contains('/identity/sync-from-platform')),
        );
        return http.Response('{"access_token":"local-tok-abc","token_type":"bearer","workspaces":[{"workspaceId":"ws-1","name":"Test","role":"founder","status":"active"}]}', 200);
      });

      final service = AuthService();
      final result = await service.syncFromPlatform(platformToken: 'plat-tok-123');

      expect(result.success, isTrue);
      expect(AuthService.isAuthenticated, isTrue);
      expect(await SecureStorageService.read('auth_token'), 'local-tok-abc');
    });

    test('syncFromPlatform surfaces 403 as not-a-member error', () async {
      ApiClient.client = MockClient((request) async => http.Response('{}', 403));

      final service = AuthService();
      final result = await service.syncFromPlatform(platformToken: 'plat-tok-123');

      expect(result.success, isFalse);
      expect(result.errorMessage, contains('thành viên'));
    });

    test('finishAuthentication returns false without touching auth_token when sync fails', () async {
      ApiClient.client = MockClient((request) async => http.Response('{}', 403));

      final service = AuthService();
      final ok = await service.finishAuthentication(platformToken: 'plat-tok-123');

      expect(ok, isFalse);
      expect(AuthService.isAuthenticated, isFalse);
    });

    // Task 4 — trước đây finishAuthenticationForWorkspace luôn trả `true` bất
    // kể getMe() thành công hay không (chỉ ghi workspace_id rồi gọi getMe()
    // không kiểm tra kết quả). Global constraint: không được nuốt lỗi
    // network/HTTP thành `true`/`null` mập mờ — trả typed AuthResult để
    // SessionController biết chính xác vì sao activation thất bại.
    test('finishAuthenticationForWorkspace returns a failed AuthResult when /identity/me is 401',
        () async {
      AuthService.setCachedToken('local-session-token');
      ApiClient.client = MockClient((request) async => http.Response('{}', 401));

      final service = AuthService();
      final result = await service.finishAuthenticationForWorkspace(
        workspaceId: 'ws-1',
      );

      expect(result.success, isFalse);
      expect(result.errorMessage, isNotNull);
    });

    test('finishAuthenticationForWorkspace returns a failed AuthResult when /identity/me is 500',
        () async {
      AuthService.setCachedToken('local-session-token');
      ApiClient.client = MockClient((request) async => http.Response('{}', 500));

      final service = AuthService();
      final result = await service.finishAuthenticationForWorkspace(
        workspaceId: 'ws-1',
      );

      expect(result.success, isFalse);
      expect(result.errorMessage, isNotNull);
    });

    test('finishAuthenticationForWorkspace returns a failed AuthResult when the response workspace does not match the target',
        () async {
      AuthService.setCachedToken('local-session-token');
      ApiClient.client = MockClient((request) async => http.Response(
            jsonEncode({
              'id': 'user-1',
              'workspaceId': 'ws-OTHER',
              'role': 'member',
            }),
            200,
          ));

      final service = AuthService();
      final result = await service.finishAuthenticationForWorkspace(
        workspaceId: 'ws-1',
      );

      expect(result.success, isFalse);
      expect(result.errorMessage, isNotNull);
    });

    test('finishAuthenticationForWorkspace returns a successful AuthResult when the workspace matches',
        () async {
      AuthService.setCachedToken('local-session-token');
      ApiClient.client = MockClient((request) async => http.Response(
            jsonEncode({
              'id': 'user-1',
              'workspaceId': 'ws-1',
              'role': 'founder',
            }),
            200,
          ));

      final service = AuthService();
      final result = await service.finishAuthenticationForWorkspace(
        workspaceId: 'ws-1',
      );

      expect(result.success, isTrue);
      expect(result.user, isNotNull);
    });
  });

  group('AuthService.validateCachedToken', () {
    tearDown(() {
      ApiClient.client = http.Client();
    });

    test('returns false immediately when no token cached (no network call)', () async {
      AuthService.setCachedToken(null);
      var called = false;
      ApiClient.client = MockClient((request) async {
        called = true;
        return http.Response('{}', 200);
      });

      final result = await AuthService.validateCachedToken();
      expect(result, isFalse);
      expect(called, isFalse);
    });

    test('returns true when /auth/me responds 200', () async {
      AuthService.setCachedToken('valid-token');
      ApiClient.client = MockClient((request) async => http.Response('{}', 200));

      final result = await AuthService.validateCachedToken();
      expect(result, isTrue);
    });

    test('returns false when /auth/me responds 401 (token het han)', () async {
      AuthService.setCachedToken('expired-token');
      ApiClient.client = MockClient((request) async => http.Response('{}', 401));

      final result = await AuthService.validateCachedToken();
      expect(result, isFalse);
    });

    test('returns null on network error (khong dang xuat oan khi mat mang)', () async {
      AuthService.setCachedToken('some-token');
      ApiClient.client = MockClient((request) async {
        throw const SocketException('no network');
      });

      final result = await AuthService.validateCachedToken();
      expect(result, isNull);
    });
  });

  group('AuthMiddleware Guard', () {
    final middleware = AuthMiddleware();

    test('redirects unauthenticated user to AppRoutes.login', () {
      AuthService.setCachedToken(null);
      final result = middleware.redirect(AppRoutes.hub);
      expect(result, isNotNull);
      expect(result?.name, AppRoutes.login);
    });

    test('allows authenticated user to access protected routes', () {
      AuthService.setCachedToken('valid-token');
      final result = middleware.redirect(AppRoutes.hub);
      expect(result, isNull);
    });
  });

  group('WorkspacePickerGuardMiddleware', () {
    final middleware = WorkspacePickerGuardMiddleware();

    tearDown(() => Get.routing.args = null);

    test('redirects to login when route arguments are missing entirely', () {
      Get.routing.args = null;
      final result = middleware.redirect(AppRoutes.workspacePicker);
      expect(result, isNotNull);
      expect(result?.name, AppRoutes.login);
    });

    test('redirects to login when platformToken is empty', () {
      Get.routing.args = {
        'platformToken': '',
        'workspaces': <WorkspaceSummary>[
          const WorkspaceSummary(
            workspaceId: 'ws-1',
            name: 'A',
            roleId: 'founder',
            status: 'active',
          ),
        ],
      };
      final result = middleware.redirect(AppRoutes.workspacePicker);
      expect(result, isNotNull);
      expect(result?.name, AppRoutes.login);
    });

    test('redirects to login when workspaces list is empty (stale arguments)', () {
      Get.routing.args = {
        'platformToken': 'plat-tok-123',
        'workspaces': <WorkspaceSummary>[],
      };
      final result = middleware.redirect(AppRoutes.workspacePicker);
      expect(result, isNotNull);
      expect(result?.name, AppRoutes.login);
    });

    test('allows the route when arguments carry a real platformToken + workspaces', () {
      Get.routing.args = {
        'platformToken': 'plat-tok-123',
        'workspaces': <WorkspaceSummary>[
          const WorkspaceSummary(
            workspaceId: 'ws-1',
            name: 'A',
            roleId: 'founder',
            status: 'active',
          ),
        ],
      };
      final result = middleware.redirect(AppRoutes.workspacePicker);
      expect(result, isNull);
    });
  });

  group('AuthController Form Validation', () {
    late AuthController controller;

    setUp(() {
      controller = AuthController();
    });

    tearDown(() {
      controller.onClose();
    });

    test('login validates empty fields', () async {
      controller.identifierController.text = '';
      controller.passwordController.text = '';

      await controller.login();
      expect(controller.errorMessage.value, contains('Vui lòng nhập đầy đủ thông tin'));
    });

    test('register validates empty display name', () async {
      controller.regDisplayNameController.text = '';
      controller.regEmailController.text = 'a@b.com';
      controller.regPasswordController.text = 'password123';
      controller.regConfirmPasswordController.text = 'password123';

      await controller.register();
      expect(controller.registerErrorMessage.value, contains('Họ và tên'));
    });

    test('register validates invalid email format', () async {
      controller.regDisplayNameController.text = 'Nguyen Van A';
      controller.regEmailController.text = 'not-an-email'; // Invalid email
      controller.regPasswordController.text = 'password123';
      controller.regConfirmPasswordController.text = 'password123';

      await controller.register();
      expect(controller.registerErrorMessage.value, contains('Email không hợp lệ'));
    });

    test('register validates short password', () async {
      controller.regDisplayNameController.text = 'Nguyen Van A';
      controller.regEmailController.text = 'a@b.com';
      controller.regPasswordController.text = '123'; // Short
      controller.regConfirmPasswordController.text = '123';

      await controller.register();
      expect(controller.registerErrorMessage.value, contains('8 đến 128'));
    });

    test('submitCompanyStep validates missing company name when creating a new company', () async {
      controller.registerStep.value = 2;
      controller.registeredPlatformToken.value = 'mock-platform-token';
      controller.isJoiningCompany.value = false;
      controller.regCompanyNameController.text = '';

      await controller.submitCompanyStep();
      expect(controller.registerErrorMessage.value, contains('công ty'));
    });

    test('submitCompanyStep validates missing invitation token when joining an existing workspace', () async {
      controller.registerStep.value = 2;
      controller.registeredPlatformToken.value = 'mock-platform-token';
      controller.isJoiningCompany.value = true;
      controller.regInvitationTokenController.text = '';

      await controller.submitCompanyStep();
      expect(controller.registerErrorMessage.value, contains('lời mời'));
    });

    // Task 6 — ô nhập của tab "Tham gia" giờ nhận invitation token (chuỗi
    // base64url), KHÔNG còn là company_id dạng số. Xác nhận input không phải
    // số (không có `int.tryParse`/keyboardType number nào chặn/cắt nó) vẫn
    // được coi là hợp lệ ở bước validate (đi tiếp tới gọi service, không bị
    // chặn ở validate như "phải là số").
    test('submitCompanyStep accepts a non-numeric base64url-looking invitation token without truncation', () async {
      controller.registerStep.value = 2;
      controller.registeredPlatformToken.value = 'mock-platform-token';
      controller.isJoiningCompany.value = true;
      controller.regInvitationTokenController.text = 'aZ9-_QW3xyzTOKEN==nonNumeric';

      ApiClient.client = MockClient((request) async {
        if (request.url.path.contains('/platform/auth/companies/invitations/accept')) {
          final decoded = jsonDecode(request.body) as Map<String, dynamic>;
          expect(decoded['token'], 'aZ9-_QW3xyzTOKEN==nonNumeric');
          return http.Response(
            '{"company_id":"1","name":"Joined Co","role_id":"member"}',
            200,
          );
        }
        return http.Response('{}', 403);
      });

      await controller.submitCompanyStep();

      // Không bị validate chặn bởi lỗi "phải là số" — thất bại (nếu có) chỉ
      // có thể đến từ bước sync-from-platform tiếp theo (403 ở mock trên),
      // không phải từ lỗi format token.
      expect(controller.registerErrorMessage.value, isNot(contains('phải là số')));

      ApiClient.client = http.Client();
    });

    test('submitAccountStep validates mismatched password confirmation', () async {
      controller.regDisplayNameController.text = 'Nguyen Van A';
      controller.regEmailController.text = 'a@b.com';
      controller.regPasswordController.text = 'password1234';
      controller.regConfirmPasswordController.text = 'password9999'; // Mismatched

      await controller.submitAccountStep();
      expect(controller.registerErrorMessage.value, contains('không trùng khớp'));
    });

    test('clearRegisterForm resets all fields and errors', () {
      controller.regDisplayNameController.text = 'Test User';
      controller.regEmailController.text = 'a@b.com';
      controller.regPasswordController.text = 'password123';
      controller.regConfirmPasswordController.text = 'password123';
      controller.regCompanyNameController.text = 'Acme';
      controller.regInvitationTokenController.text = 'inv-tok-42';
      controller.isJoiningCompany.value = true;
      controller.registerErrorMessage.value = 'Some error';

      controller.clearRegisterForm();

      expect(controller.regDisplayNameController.text, isEmpty);
      expect(controller.regEmailController.text, isEmpty);
      expect(controller.regPasswordController.text, isEmpty);
      expect(controller.regConfirmPasswordController.text, isEmpty);
      expect(controller.regCompanyNameController.text, isEmpty);
      expect(controller.regInvitationTokenController.text, isEmpty);
      expect(controller.isJoiningCompany.value, isFalse);
      expect(controller.registerErrorMessage.value, isEmpty);
    });
  });
}
