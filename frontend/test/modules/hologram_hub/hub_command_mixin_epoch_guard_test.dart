// Fix (2026-09-02, epoch-guard siblings) — reviewer độc lập phát hiện
// `HubCommandMixin` (sibling của `HubControlPlaneMixin`, đã guard ở
// `hub_control_plane_mixin_epoch_guard_test.dart`) có CÙNG lỗ hổng: các hàm
// `load*()` (`loadHubSummary`, `loadCeoNextActions`, ...) gọi API rồi ghi
// thẳng kết quả vào Rx state mà KHÔNG kiểm tra "response này có còn thuộc
// workspace hiện tại không". Nếu một request cho workspace CŨ đang bay khi
// `SessionController.activateWorkspace`/`logout` chạy, response trả về SAU
// khi reset sẽ ghi đè dữ liệu workspace CŨ (hub summary, CEO next actions —
// dữ liệu tenant-specific thật) lên state vừa xoá cho workspace MỚI.
//
// Test này dùng `Completer` để giữ `loadCeoNextActions()` và
// `loadHubSummary()` "in-flight" thật sự, chuyển workspace TRONG LÚC còn
// pending, rồi mới hoàn thành request cũ — chứng minh qua timing thật rằng
// Rx state KHÔNG bị dữ liệu workspace CŨ ghi đè.
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
import 'package:frontend/modules/dashboard/services/hub_service.dart';
import 'package:frontend/modules/hologram_hub/controllers/hologram_hub_controller.dart';
import 'package:frontend/modules/strategy/models/strategy_list_result.dart';
import 'package:frontend/modules/strategy/services/strategy_service.dart';

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

/// Fake `HubService` cho phép test giữ `getHubSummary()` "in-flight" tuỳ ý
/// qua một `Completer` bên ngoài, thay vì phụ thuộc vào timing thật của
/// network.
class _DelayedHubService extends HubService {
  _DelayedHubService(this._pending);

  final Completer<Map<String, dynamic>?> _pending;

  @override
  Future<Map<String, dynamic>?> getHubSummary() => _pending.future;
}

/// Fake `StrategyService` cho phép test giữ `getCeoNextActions()` "in-flight"
/// tuỳ ý qua một `Completer` bên ngoài.
class _DelayedCeoNextActionsService extends StrategyService {
  _DelayedCeoNextActionsService(this._pending);

  final Completer<StrategyListResult<Map<String, dynamic>>> _pending;

  @override
  Future<StrategyListResult<Map<String, dynamic>>> getCeoNextActions({
    int limit = 5,
  }) =>
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
      'loadHubSummary() discards a stale in-flight response after workspace switch (generation guard)',
      () async {
    final session = Get.put<SessionController>(
      SessionController(contextService: _SucceedingContextService()),
    );

    final pendingOld = Completer<Map<String, dynamic>?>();
    final hub = HologramHubController(
      hubService: _DelayedHubService(pendingOld),
    );

    final staleLoad = hub.loadHubSummary(showLoading: false);

    await Future<void>.delayed(Duration.zero);
    expect(hub.hubSummary.value, isNull,
        reason: 'chưa có response nào trả về, state phải còn null');

    final generationBeforeSwitch = session.workspaceGeneration;
    final activation = await session.activateWorkspace('workspace-b');
    expect(activation.isSuccess, isTrue);
    expect(session.workspaceGeneration, greaterThan(generationBeforeSwitch));

    pendingOld.complete({'stale': 'workspace-a hub summary'});
    await staleLoad;

    expect(
      hub.hubSummary.value,
      isNull,
      reason:
          'response trả về SAU khi workspace đã chuyển phải bị bỏ qua, không được ghi đè Rx state',
    );
  });

  test(
      'loadHubSummary() still writes the response when the generation has NOT changed (guard is not overly aggressive)',
      () async {
    Get.put<SessionController>(
      SessionController(contextService: _SucceedingContextService()),
    );

    final pending = Completer<Map<String, dynamic>?>();
    final hub = HologramHubController(
      hubService: _DelayedHubService(pending),
    );

    final load = hub.loadHubSummary(showLoading: false);
    await Future<void>.delayed(Duration.zero);

    pending.complete({'fresh': 'workspace-a hub summary'});
    await load;

    expect(hub.hubSummary.value, isNotNull);
    expect(hub.hubSummary.value!['fresh'], 'workspace-a hub summary');
  });

  test(
      'loadCeoNextActions() discards a stale in-flight response after workspace switch (generation guard)',
      () async {
    final session = Get.put<SessionController>(
      SessionController(contextService: _SucceedingContextService()),
    );

    final pendingOld =
        Completer<StrategyListResult<Map<String, dynamic>>>();
    final hub = HologramHubController(
      strategyService: _DelayedCeoNextActionsService(pendingOld),
    );

    final staleLoad = hub.loadCeoNextActions();

    await Future<void>.delayed(Duration.zero);
    expect(hub.ceoNextActions, isEmpty,
        reason: 'chưa có response nào trả về, state phải còn rỗng');

    final generationBeforeSwitch = session.workspaceGeneration;
    final activation = await session.activateWorkspace('workspace-b');
    expect(activation.isSuccess, isTrue);
    expect(session.workspaceGeneration, greaterThan(generationBeforeSwitch));

    pendingOld.complete(
      const StrategyListResult.success([
        {'id': 'stale-action', 'title': 'workspace-a stale CEO action'},
      ]),
    );
    await staleLoad;

    expect(
      hub.ceoNextActions,
      isEmpty,
      reason:
          'response trả về SAU khi workspace đã chuyển phải bị bỏ qua, không được ghi đè Rx state',
    );
  });

  test(
      'loadCeoNextActions() still writes the response when the generation has NOT changed (guard is not overly aggressive)',
      () async {
    Get.put<SessionController>(
      SessionController(contextService: _SucceedingContextService()),
    );

    final pending = Completer<StrategyListResult<Map<String, dynamic>>>();
    final hub = HologramHubController(
      strategyService: _DelayedCeoNextActionsService(pending),
    );

    final load = hub.loadCeoNextActions();
    await Future<void>.delayed(Duration.zero);

    pending.complete(
      const StrategyListResult.success([
        {'id': 'fresh-action', 'title': 'workspace-a fresh CEO action'},
      ]),
    );
    await load;

    expect(hub.ceoNextActions, hasLength(1));
    expect(
      (hub.ceoNextActions.first as Map)['title'],
      'workspace-a fresh CEO action',
    );
  });
}
