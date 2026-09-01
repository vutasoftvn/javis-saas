import 'dart:convert';
import 'dart:io';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:frontend/core/network/api_client.dart';
import 'package:frontend/modules/auth/services/auth_service.dart';
import 'package:frontend/core/routing/auth_middleware.dart';
import 'package:frontend/core/routing/app_routes.dart';
import 'package:frontend/modules/auth/controllers/auth_controller.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() {
    SharedPreferences.setMockInitialValues({});
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

    test('loginPlatform returns platform token on success (does not cache it as auth_token)', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.url.path, contains('/platform/auth/sessions'));
        return http.Response('{"access_token":"plat-tok-123","token_type":"bearer"}', 200);
      });

      final service = AuthService();
      final result = await service.loginPlatform('founder@cosa.dev', 'pw');

      expect(result.success, isTrue);
      expect(result.token, 'plat-tok-123');
      expect(AuthService.isAuthenticated, isFalse); // chua sync-from-platform nen chua co auth_token local
    });

    test('loginPlatform surfaces 401 as a friendly error', () async {
      ApiClient.client = MockClient((request) async => http.Response('{}', 401));

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

      // Token is cached; company_id never appears
      expect(AuthService.isAuthenticated, isTrue);
      final prefs = await SharedPreferences.getInstance();
      expect(prefs.getString('auth_token'), 'local-jwt-123');
      expect(prefs.getString('company_id'), isNull);
    });

    test('registerPlatform sends company_name and returns company_id from server', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.url.path, contains('/platform/auth/register'));
        return http.Response(
          '{"access_token":"plat-tok-999","token_type":"bearer","company_id":"42"}',
          200,
        );
      });

      final service = AuthService();
      final result = await service.registerPlatform(
        email: 'founder@cosa.dev',
        password: 'secretpw',
        displayName: 'Founder',
        companyName: 'Acme Inc',
      );

      expect(result.success, isTrue);
      expect(result.token, 'plat-tok-999');
      expect(result.companyId, '42');
    });

    test('registerPlatform surfaces 409 as email-taken error', () async {
      ApiClient.client = MockClient((request) async => http.Response('{}', 409));

      final service = AuthService();
      final result = await service.registerPlatform(
        email: 'founder@cosa.dev',
        password: 'secretpw',
        displayName: 'Founder',
        companyName: 'Acme',
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

    test('joinCompany joins existing company and returns companyId', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.url.path, contains('/platform/auth/companies/join'));
        expect(request.headers['Authorization'], 'Bearer plat-tok-123');
        return http.Response(
          '{"company_id":"999","name":"Joined Co","role_id":"user"}',
          200,
        );
      });

      final service = AuthService();
      final result = await service.joinCompany(platformToken: 'plat-tok-123', companyId: '999');

      expect(result.success, isTrue);
      expect(result.companyId, '999');
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
      final prefs = await SharedPreferences.getInstance();
      expect(prefs.getString('auth_token'), 'local-tok-abc');
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

    test('submitCompanyStep validates missing join code when joining an existing company', () async {
      controller.registerStep.value = 2;
      controller.registeredPlatformToken.value = 'mock-platform-token';
      controller.isJoiningCompany.value = true;
      controller.regJoinCompanyIdController.text = '';

      await controller.submitCompanyStep();
      expect(controller.registerErrorMessage.value, contains('công ty'));
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
      controller.regJoinCompanyIdController.text = '42';
      controller.isJoiningCompany.value = true;
      controller.registerErrorMessage.value = 'Some error';

      controller.clearRegisterForm();

      expect(controller.regDisplayNameController.text, isEmpty);
      expect(controller.regEmailController.text, isEmpty);
      expect(controller.regPasswordController.text, isEmpty);
      expect(controller.regConfirmPasswordController.text, isEmpty);
      expect(controller.regCompanyNameController.text, isEmpty);
      expect(controller.regJoinCompanyIdController.text, isEmpty);
      expect(controller.isJoiningCompany.value, isFalse);
      expect(controller.registerErrorMessage.value, isEmpty);
    });
  });
}
