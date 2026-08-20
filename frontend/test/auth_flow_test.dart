import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
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
        'brain_id': 'brain-456',
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
      controller.regPhoneController.text = '0912345678';
      controller.regPasswordController.text = 'password123';
      controller.regConfirmPasswordController.text = 'password123';

      await controller.register();
      expect(controller.registerErrorMessage.value, contains('Họ và tên'));
    });

    test('register validates invalid phone format', () async {
      controller.regDisplayNameController.text = 'Nguyen Van A';
      controller.regPhoneController.text = '123'; // Invalid phone
      controller.regPasswordController.text = 'password123';
      controller.regConfirmPasswordController.text = 'password123';

      await controller.register();
      expect(controller.registerErrorMessage.value, contains('Số điện thoại không hợp lệ'));
    });

    test('register validates short password', () async {
      controller.regDisplayNameController.text = 'Nguyen Van A';
      controller.regPhoneController.text = '0912345678';
      controller.regPasswordController.text = '123'; // Short
      controller.regConfirmPasswordController.text = '123';

      await controller.register();
      expect(controller.registerErrorMessage.value, contains('ít nhất 6 ký tự'));
    });

    test('register validates mismatched password confirmation', () async {
      controller.regDisplayNameController.text = 'Nguyen Van A';
      controller.regPhoneController.text = '0912345678';
      controller.regPasswordController.text = 'password123';
      controller.regConfirmPasswordController.text = 'password999'; // Mismatched

      await controller.register();
      expect(controller.registerErrorMessage.value, contains('không trùng khớp'));
    });

    test('clearRegisterForm resets all fields and errors', () {
      controller.regDisplayNameController.text = 'Test User';
      controller.regPhoneController.text = '0912345678';
      controller.regPasswordController.text = 'password123';
      controller.regConfirmPasswordController.text = 'password123';
      controller.registerErrorMessage.value = 'Some error';

      controller.clearRegisterForm();

      expect(controller.regDisplayNameController.text, isEmpty);
      expect(controller.regPhoneController.text, isEmpty);
      expect(controller.regPasswordController.text, isEmpty);
      expect(controller.regConfirmPasswordController.text, isEmpty);
      expect(controller.registerErrorMessage.value, isEmpty);
    });
  });
}
