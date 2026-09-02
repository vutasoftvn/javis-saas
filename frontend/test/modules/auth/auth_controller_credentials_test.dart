import 'package:flutter_test/flutter_test.dart';
import 'package:get/get.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:frontend/core/network/api_client.dart';
import 'package:frontend/core/session/session_context_service.dart';
import 'package:frontend/core/session/session_controller.dart';
import 'package:frontend/core/session/session_snapshot.dart';
import 'package:frontend/modules/auth/controllers/auth_controller.dart';
import 'package:frontend/modules/auth/services/auth_service.dart';

/// Task 4 — `AuthController.login` (single-workspace path) đi qua
/// `SessionController.activateWorkspace` thay vì gọi
/// `AuthService.finishAuthenticationForWorkspace` trực tiếp. Test này chỉ
/// quan tâm hành vi lưu credentials (không bao giờ lưu plaintext password),
/// không phải transaction xác minh workspace (đã có
/// `test/core/session/session_controller_test.dart` cho việc đó), nên fake
/// SessionController luôn thành công ngay, không đụng network.
class _AlwaysSucceedsSessionController extends SessionController {
  _AlwaysSucceedsSessionController()
      : super(contextService: _UnusedContextService());

  @override
  Future<SessionActivationResult> activateWorkspace(String workspaceId) async {
    return SessionActivationResult.success(
      SessionSnapshot(
        userId: 'user-1',
        workspaceId: workspaceId,
        role: 'founder',
        runtime: const SessionRuntimeInfo(
          mode: 'LOCAL_ONLY',
          modeSource: 'inferred',
          presenceStatus: 'ONLINE',
          lastHeartbeatAt: null,
          asOf: null,
        ),
        capabilities: const [],
      ),
    );
  }
}

class _UnusedContextService implements SessionContextService {
  @override
  Future<SessionSnapshot> fetch(String workspaceId) =>
      throw StateError('should not be called — activateWorkspace is overridden');
}

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

        final controller = AuthController(
          sessionController: _AlwaysSucceedsSessionController(),
        );
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
