// Fix (2026-09-02, epoch-guard siblings) — reviewer độc lập phát hiện
// `HubStageMixin` (sibling của `HubControlPlaneMixin`, đã guard ở
// `hub_control_plane_mixin_epoch_guard_test.dart`) có CÙNG lỗ hổng:
// `loadStageContext`/`loadProjectsList` gọi API rồi ghi thẳng kết quả vào Rx
// state mà KHÔNG kiểm tra "response này có còn thuộc workspace hiện tại
// không". Nếu một request cho workspace CŨ đang bay khi
// `SessionController.activateWorkspace`/`logout` chạy, response trả về SAU
// khi reset sẽ ghi đè dữ liệu workspace CŨ (stage context, danh sách dự án —
// dữ liệu tenant-specific thật) lên state vừa xoá cho workspace MỚI.
//
// Test này dùng `Completer` để giữ `loadProjectsList()` và
// `loadStageContext()` "in-flight" thật sự, chuyển workspace TRONG LÚC còn
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
import 'package:frontend/data/models/stage_model.dart';
import 'package:frontend/modules/auth/services/auth_service.dart';
import 'package:frontend/modules/hologram_hub/controllers/hologram_hub_controller.dart';
import 'package:frontend/modules/strategy/models/strategy_list_result.dart';
import 'package:frontend/modules/strategy/services/stage_service.dart';
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

/// Fake `StrategyService` cho phép test giữ `getProjects()` "in-flight" tuỳ ý
/// qua một `Completer` bên ngoài.
class _DelayedProjectsService extends StrategyService {
  _DelayedProjectsService(this._pending);

  final Completer<StrategyListResult<Map<String, dynamic>>> _pending;

  @override
  Future<StrategyListResult<Map<String, dynamic>>> getProjects() =>
      _pending.future;
}

/// Fake `StageService` cho phép test giữ `getStageContext()` "in-flight" tuỳ
/// ý qua một `Completer` bên ngoài.
class _DelayedStageService extends StageService {
  _DelayedStageService(this._pending);

  final Completer<StageContextModel?> _pending;

  @override
  Future<StageContextModel?> getStageContext({int? projectId}) =>
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
      'loadProjectsList() discards a stale in-flight response after workspace switch (generation guard)',
      () async {
    final session = Get.put<SessionController>(
      SessionController(contextService: _SucceedingContextService()),
    );

    final pendingOld = Completer<StrategyListResult<Map<String, dynamic>>>();
    final hub = HologramHubController(
      strategyService: _DelayedProjectsService(pendingOld),
    );

    final staleLoad = hub.loadProjectsList();

    await Future<void>.delayed(Duration.zero);
    expect(hub.projectsList, isEmpty,
        reason: 'chưa có response nào trả về, state phải còn rỗng');

    final generationBeforeSwitch = session.workspaceGeneration;
    final activation = await session.activateWorkspace('workspace-b');
    expect(activation.isSuccess, isTrue);
    expect(session.workspaceGeneration, greaterThan(generationBeforeSwitch));

    pendingOld.complete(
      const StrategyListResult.success([
        {'id': 1, 'title': 'workspace-a stale project'},
      ]),
    );
    await staleLoad;

    expect(
      hub.projectsList,
      isEmpty,
      reason:
          'response trả về SAU khi workspace đã chuyển phải bị bỏ qua, không được ghi đè Rx state',
    );
  });

  test(
      'loadProjectsList() still writes the response when the generation has NOT changed (guard is not overly aggressive)',
      () async {
    Get.put<SessionController>(
      SessionController(contextService: _SucceedingContextService()),
    );

    final pending = Completer<StrategyListResult<Map<String, dynamic>>>();
    final hub = HologramHubController(
      strategyService: _DelayedProjectsService(pending),
    );

    final load = hub.loadProjectsList();
    await Future<void>.delayed(Duration.zero);

    pending.complete(
      const StrategyListResult.success([
        {'id': 2, 'title': 'workspace-a fresh project'},
      ]),
    );
    await load;

    expect(hub.projectsList, hasLength(1));
    expect(hub.projectsList.first['title'], 'workspace-a fresh project');
  });

  test(
      'loadStageContext() discards a stale in-flight response after workspace switch (generation guard)',
      () async {
    final session = Get.put<SessionController>(
      SessionController(contextService: _SucceedingContextService()),
    );

    final pendingOld = Completer<StageContextModel?>();
    final hub = HologramHubController(
      stageService: _DelayedStageService(pendingOld),
    );

    final staleLoad = hub.loadStageContext();

    await Future<void>.delayed(Duration.zero);
    expect(hub.stageContext.value, isNull,
        reason: 'chưa có response nào trả về, state phải còn null');

    final generationBeforeSwitch = session.workspaceGeneration;
    final activation = await session.activateWorkspace('workspace-b');
    expect(activation.isSuccess, isTrue);
    expect(session.workspaceGeneration, greaterThan(generationBeforeSwitch));

    pendingOld.complete(
      StageContextModel.fromJson({
        'project_id': 999,
        'project_title': 'workspace-a stale project',
      }),
    );
    await staleLoad;

    expect(
      hub.stageContext.value,
      isNull,
      reason:
          'response trả về SAU khi workspace đã chuyển phải bị bỏ qua, không được ghi đè Rx state',
    );
    expect(
      hub.selectedProjectId.value,
      isNull,
      reason:
          'selectedProjectId cũng phải bị bỏ qua — không chỉ riêng stageContext',
    );
  });

  test(
      'loadStageContext() still writes the response when the generation has NOT changed (guard is not overly aggressive)',
      () async {
    Get.put<SessionController>(
      SessionController(contextService: _SucceedingContextService()),
    );

    final pending = Completer<StageContextModel?>();
    final hub = HologramHubController(
      stageService: _DelayedStageService(pending),
    );

    final load = hub.loadStageContext();
    await Future<void>.delayed(Duration.zero);

    pending.complete(
      StageContextModel.fromJson({
        'project_id': 42,
        'project_title': 'workspace-a fresh project',
      }),
    );
    await load;

    expect(hub.stageContext.value, isNotNull);
    expect(hub.stageContext.value!.projectTitle, 'workspace-a fresh project');
    expect(hub.selectedProjectId.value, 42);
  });
}
