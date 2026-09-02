// Fix (2026-09-02, epoch-guard) — reviewer độc lập phát hiện race window còn
// sót lại sau task `resetForWorkspace()`: các hàm `load*()` trong
// `HubControlPlaneMixin` gọi API rồi ghi thẳng kết quả vào Rx state mà KHÔNG
// kiểm tra "response này có còn thuộc workspace hiện tại không". Nếu một
// request cho workspace CŨ đang bay (network RTT) khi
// `SessionController.activateWorkspace`/`logout` chạy, response trả về SAU
// khi reset sẽ ghi đè dữ liệu workspace CŨ lên state vừa xoá cho workspace
// MỚI.
//
// Test này dùng `Completer` để giữ một `loadWorkProducts()` "in-flight" thật
// sự (không resolve ngay), chuyển workspace TRONG LÚC nó còn pending, rồi mới
// hoàn thành request cũ với dữ liệu cũ — chứng minh qua timing thật rằng
// `workProducts` KHÔNG bị dữ liệu workspace CŨ ghi đè.
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
import 'package:frontend/modules/agents/services/agent_platform_service.dart';
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

/// Fake `AgentPlatformService` cho phép test giữ `listWorkProducts()`
/// "in-flight" tuỳ ý qua một `Completer` bên ngoài, thay vì phụ thuộc vào
/// timing thật của network.
class _DelayedWorkProductsService extends AgentPlatformService {
  _DelayedWorkProductsService(this._pending);

  final Completer<List<Map<String, dynamic>>> _pending;

  @override
  Future<List<Map<String, dynamic>>> listWorkProducts({String? status}) =>
      _pending.future;
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
      'loadWorkProducts() discards a stale in-flight response after workspace switch (generation guard)',
      () async {
    final session = Get.put<SessionController>(
      SessionController(contextService: _SucceedingContextService()),
    );

    final pendingOld = Completer<List<Map<String, dynamic>>>();
    final hub = HologramHubController(
      agentPlatformService: _DelayedWorkProductsService(pendingOld),
    );

    // KHÔNG đăng ký `hub` qua Get.put — test này cô lập đúng guard trong
    // `HubControlPlaneMixin.loadWorkProducts()`, không phụ thuộc vào bước
    // `resetForWorkspace()` (đã có test riêng chứng minh ở
    // `hologram_hub_controller_exit_cleanup_test.dart` /
    // `session_controller_shell_reset_test.dart`).

    // 1) Bắt đầu một load cho workspace-a — request "bay" mãi cho tới khi ta
    //    tự complete Completer bên dưới.
    final staleLoad = hub.loadWorkProducts();

    // Để chắc chắn `loadWorkProducts` đã capture generation VÀ đang thật sự
    // await bên trong `_pending.future` (không phải chạy đồng bộ xong luôn).
    await Future<void>.delayed(Duration.zero);
    expect(hub.workProducts, isEmpty,
        reason: 'chưa có response nào trả về, state phải còn rỗng');

    // 2) Chuyển sang workspace-b TRONG LÚC request cũ còn pending — điều này
    //    tăng `workspaceGeneration` của SessionController.
    final generationBeforeSwitch = session.workspaceGeneration;
    final activation = await session.activateWorkspace('workspace-b');
    expect(activation.isSuccess, isTrue);
    expect(session.workspaceGeneration, greaterThan(generationBeforeSwitch));

    // 3) CHỈ BÂY GIỜ mới hoàn thành request cũ, với dữ liệu của workspace-a.
    pendingOld.complete([
      {'id': 1, 'title': 'workspace-a stale work product'},
    ]);
    await staleLoad;

    // 4) Dữ liệu cũ phải bị discard — generation đã đổi giữa lúc await.
    expect(
      hub.workProducts,
      isEmpty,
      reason:
          'response trả về SAU khi workspace đã chuyển phải bị bỏ qua, không được ghi đè Rx state',
    );
  });

  test(
      'loadWorkProducts() still writes the response when the generation has NOT changed (guard is not overly aggressive)',
      () async {
    Get.put<SessionController>(
      SessionController(contextService: _SucceedingContextService()),
    );

    final pending = Completer<List<Map<String, dynamic>>>();
    final hub = HologramHubController(
      agentPlatformService: _DelayedWorkProductsService(pending),
    );

    final load = hub.loadWorkProducts();
    await Future<void>.delayed(Duration.zero);

    // Không có switch/logout nào xảy ra — hoàn thành request bình thường.
    pending.complete([
      {'id': 2, 'title': 'workspace-a fresh work product'},
    ]);
    await load;

    expect(hub.workProducts, hasLength(1));
    expect(hub.workProducts.first['title'], 'workspace-a fresh work product');
  });
}
