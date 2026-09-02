// Fix (2026-09-02, epoch-guard full audit) — `HubAuthMixin.ensureAuthenticated`
// awaits `authService.getMe()` rồi ghi `userName`/`userRole`. Vì
// `HologramHubController` là `permanent: true` (không bị Get huỷ giữa các
// lần logout/login), một response `getMe()` chậm của phiên/tài khoản TRƯỚC
// vẫn có thể ghi đè tên/role hiển thị của phiên hiện tại nếu nó về SAU khi
// một workspace mới đã được kích hoạt trong lúc chờ. Test dùng `Completer`
// để giữ `getMe()` "in-flight" thật sự, activate workspace mới TRONG LÚC còn
// pending, rồi mới complete request cũ — chứng minh `userName`/`userRole`
// không bị ghi đè.
import 'dart:async';
import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:get/get.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:frontend/core/network/api_client.dart';
import 'package:frontend/core/services/secure_storage_service.dart';
import 'package:frontend/core/session/session_context_service.dart';
import 'package:frontend/core/session/session_controller.dart';
import 'package:frontend/core/session/session_snapshot.dart';
import 'package:frontend/modules/auth/services/auth_service.dart';
import 'package:frontend/modules/hologram_hub/controllers/hologram_hub_controller.dart';

import '../../core/services/fakes/fake_secret_store.dart';

SessionSnapshot _snapshotFor(String workspaceId) => SessionSnapshot(
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
      capabilities: const ['workspace.session.read'],
    );

class _SucceedingContextService implements SessionContextService {
  @override
  Future<SessionSnapshot> fetch(String workspaceId) async =>
      _snapshotFor(workspaceId);
}

/// Fake `AuthService` giữ `getMe()` "in-flight" tuỳ ý qua một `Completer`
/// bên ngoài, để test kiểm soát chính xác thời điểm response trả về.
class _DelayedAuthService extends AuthService {
  _DelayedAuthService(this._pending);
  final Completer<Map<String, dynamic>?> _pending;

  @override
  Future<Map<String, dynamic>?> getMe() => _pending.future;
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  Get.testMode = true;

  late http.Client originalClient;

  setUp(() {
    SharedPreferences.setMockInitialValues({'workspace_id': 'workspace-a'});
    SecureStorageService.configureForTest(FakeSecretStore());
    AuthService.setCachedToken('fake-token-for-epoch-guard-test');
    originalClient = ApiClient.client;
    ApiClient.client = MockClient((request) async {
      if (request.url.path.contains('/identity/me')) {
        return http.Response(
          jsonEncode({
            'id': 'user-1',
            'workspaceId': 'workspace-b',
            'role': 'founder',
          }),
          200,
        );
      }
      return http.Response('{}', 200);
    });
  });

  tearDown(() {
    ApiClient.client = originalClient;
    ApiClient.clearRuntimeContext();
    AuthService.setCachedToken(null);
    SecureStorageService.resetForTest();
    Get.reset();
  });

  test(
      'ensureAuthenticated() discards a stale in-flight getMe() response after workspace switch (generation guard)',
      () async {
    final session = Get.put<SessionController>(
      SessionController(contextService: _SucceedingContextService()),
    );

    final pendingOld = Completer<Map<String, dynamic>?>();
    final hub = HologramHubController(
      authService: _DelayedAuthService(pendingOld),
    );

    final staleCall = hub.ensureAuthenticated();
    await Future<void>.delayed(Duration.zero);
    // Giá trị mặc định khi chưa có response nào.
    expect(hub.userName.value, 'Dzu Nguyen');
    expect(hub.userRole.value, 'Founder Mode');

    final activation = await session.activateWorkspace('workspace-b');
    expect(activation.isSuccess, isTrue);

    pendingOld.complete({
      'display_name': 'Người dùng workspace-a CŨ',
      'role': 'operator',
    });
    await staleCall;

    expect(
      hub.userName.value,
      'Dzu Nguyen',
      reason:
          'response trả về SAU khi workspace đã chuyển phải bị bỏ qua, không được ghi đè userName',
    );
    expect(hub.userRole.value, 'Founder Mode');
  });

  test(
      'ensureAuthenticated() still writes the response when the generation has NOT changed',
      () async {
    Get.put<SessionController>(
      SessionController(contextService: _SucceedingContextService()),
    );

    final pending = Completer<Map<String, dynamic>?>();
    final hub = HologramHubController(authService: _DelayedAuthService(pending));

    final call = hub.ensureAuthenticated();
    await Future<void>.delayed(Duration.zero);

    pending.complete({
      'display_name': 'Người dùng workspace-a mới',
      'role': 'admin',
    });
    await call;

    expect(hub.userName.value, 'Người dùng workspace-a mới');
    expect(hub.userRole.value, 'Founder Mode'); // role == 'admin' -> Founder Mode
  });
}
