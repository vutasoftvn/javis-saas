import 'package:flutter_test/flutter_test.dart';
import 'package:get/get.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:frontend/core/network/api_client.dart';
import 'package:frontend/core/services/secure_storage_service.dart';
import 'package:frontend/modules/auth/services/auth_service.dart';
import 'package:frontend/modules/hologram_hub/controllers/founder_command_center_controller.dart';

import '../../core/services/fakes/fake_secret_store.dart';

/// Review 2026-09-27 G-4 — backend trả 429 khi vượt rate limit tạo run; chat
/// phải báo rõ thay vì hiện exception thô.
void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  late http.Client original;

  setUp(() {
    SharedPreferences.setMockInitialValues({'workspace_id': 'ws_1'});
    SecureStorageService.configureForTest(FakeSecretStore());
    AuthService.setCachedToken('fake-token');
    Get.testMode = true;
    Get.reset();
    original = ApiClient.client;
    ApiClient.client = MockClient((req) async {
      if (req.method == 'POST' && req.url.path.endsWith('/messages')) {
        return http.Response(
          '{"detail":{"code":"RATE_LIMITED"}}',
          429,
          headers: {'retry-after': '5'},
        );
      }
      return http.Response('{}', 200);
    });
  });
  tearDown(() {
    ApiClient.client = original;
    Get.reset();
  });

  test('429 on send shows a friendly rate-limit message', () async {
    final c = FounderCommandCenterController();
    c.activeProjectId.value = 'proj-1';
    c.seedConversationIdForTest('conv_1');
    await c.sendChatMessage('Lập kế hoạch tuần');
    final last = c.chatMessages.last;
    expect(last['role'], 'error');
    expect(last['content'], contains('quá nhiều yêu cầu'));
    expect(last['content'], isNot(contains('AgentChatApiException')));
    expect(c.isChatLoading.value, isFalse);
  });
}
