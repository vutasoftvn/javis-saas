import 'package:flutter_test/flutter_test.dart';
import 'package:get/get.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:frontend/core/network/api_client.dart';
import 'package:frontend/modules/auth/controllers/auth_controller.dart';
import 'package:frontend/modules/auth/services/auth_service.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  Get.testMode = true;

  group('AuthController credentials migration (no plaintext password)', () {
    tearDown(() {
      ApiClient.client = http.Client();
      AuthService.setCachedToken(null);
    });

    test(
      'legacy saved_password is deleted on init, identifier preserved, password field stays empty',
      () async {
        // Simulate an existing install from before the fix: both legacy keys present.
        SharedPreferences.setMockInitialValues({
          'saved_identifier': 'founder@example.com',
          'saved_password': 'super-secret-plaintext',
        });

        // GetxController.onInit() chỉ được framework GetX gọi khi controller
        // được đăng ký qua Get.put()/binding — khởi tạo trực tiếp bằng
        // constructor như dưới đây KHÔNG tự gọi onInit(), nên phải gọi tay để
        // kích hoạt _loadSavedCredentials() giống hành vi thật lúc app chạy.
        final controller = AuthController();
        controller.onInit();
        await Future<void>.delayed(const Duration(milliseconds: 50));

        final prefs = await SharedPreferences.getInstance();

        expect(prefs.getString('saved_identifier'), 'founder@example.com');
        expect(prefs.containsKey('saved_password'), isFalse);
        expect(controller.passwordController.text, isEmpty);
        expect(controller.identifierController.text, 'founder@example.com');
        expect(controller.rememberMe.value, isTrue);

        controller.onClose();
      },
    );

    test(
      'Remember-me login persists only saved_identifier, never saved_password',
      () async {
        SharedPreferences.setMockInitialValues({});

        ApiClient.client = MockClient((request) async {
          if (request.url.path.contains('/platform/auth/sessions')) {
            return http.Response('{"access_token":"plat-tok-123","token_type":"bearer"}', 200);
          }
          if (request.url.path.contains('/identity/sync-from-platform')) {
            return http.Response(
              '{"access_token":"local-jwt-123","token_type":"bearer","workspaces":[{"workspaceId":"ws-1","name":"Workspace A","role":"founder","status":"active"}]}',
              200,
            );
          }
          return http.Response('{}', 404);
        });

        final controller = AuthController();
        await Future<void>.delayed(Duration.zero);

        controller.rememberMe.value = true;
        await controller.login('founder@example.com', 'super-secret-plaintext');

        final prefs = await SharedPreferences.getInstance();
        expect(prefs.getString('saved_identifier'), 'founder@example.com');
        expect(prefs.containsKey('saved_password'), isFalse);
        expect(controller.errorMessage.value, isEmpty);

        controller.onClose();
      },
    );
  });
}
