// Fix (2026-09-02, epoch-guard full audit) — audit toàn bộ 7 mixin còn lại
// của `HologramHubController` phát hiện `loadEvidenceData`
// (`HubEvidenceMixin`), `loadStageLensesData` (`HubLensesMixin`),
// `loadStageGateData` + `runStageGateAudit` (`HubGateMixin`) và
// `loadTwelveWyDashboard` (`HubTwelveWyMixin`) đều gọi API rồi ghi thẳng kết
// quả (dữ liệu tenant-specific thật: hypotheses, evidences, assumption
// matrix, decisions, stage-lens summary, stage-gate audit/alerts, dashboard
// 12 Tuần) vào Rx state mà KHÔNG kiểm tra "response này có còn thuộc
// workspace hiện tại không" — cùng lỗ hổng đã fix ở `HubControlPlaneMixin`/
// `HubCommandMixin`/`HubStageMixin`.
//
// Đặc biệt: `loadEvidenceData`/`loadStageLensesData`/`loadStageGateData` từng
// được `HubStageMixin.loadStageContext()` (đã guard ở commit trước) gọi tới,
// nhưng guard của caller KHÔNG tự bảo vệ await riêng của hàm được nó gọi —
// mỗi hàm này giờ có guard riêng.
//
// Test dùng `Completer` để giữ request "in-flight" thật sự, switch workspace
// TRONG LÚC pending, rồi mới complete request cũ — chứng minh qua timing thật
// rằng Rx state không bị dữ liệu workspace CŨ ghi đè.
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
import 'package:frontend/data/models/evidence_model.dart';
import 'package:frontend/data/models/stage_gate_model.dart';
import 'package:frontend/data/models/strategy_lens_model.dart';
import 'package:frontend/data/models/twelve_wy_model.dart';
import 'package:frontend/modules/auth/services/auth_service.dart';
import 'package:frontend/modules/hologram_hub/controllers/hologram_hub_controller.dart';
import 'package:frontend/modules/strategy/services/stage_gate_service.dart';
import 'package:frontend/modules/strategy/services/strategy_lens_service.dart';
import 'package:frontend/modules/strategy/services/twelve_wy_service.dart';
import 'package:frontend/modules/vault/services/evidence_service.dart';

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

/// Fake `EvidenceService` giữ `getHypotheses()` in-flight — vì
/// `loadEvidenceData` gọi 4 API tuần tự, việc giữ mỗi await ĐẦU TIÊN đã đủ để
/// chứng minh guard chặn được response chậm (các await sau không bao giờ
/// chạy tới nếu generation đã lệch).
class _DelayedEvidenceService extends EvidenceService {
  _DelayedEvidenceService(this._pending);
  final Completer<List<HypothesisModel>> _pending;

  @override
  Future<List<HypothesisModel>> getHypotheses({
    dynamic projectId,
    dynamic workspaceId,
    String? category,
    String? status,
  }) =>
      _pending.future;
}

class _DelayedLensService extends StrategyLensService {
  _DelayedLensService(this._pending);
  final Completer<StageLensSummaryModel?> _pending;

  @override
  Future<StageLensSummaryModel?> getStageLensSummary(int projectId) =>
      _pending.future;
}

class _DelayedGateAlertsService extends StageGateService {
  _DelayedGateAlertsService(this._pending);
  final Completer<List<PrematureAlertModel>> _pending;

  @override
  Future<List<PrematureAlertModel>> getGuardrailAlerts(dynamic projectId) =>
      _pending.future;
}

class _DelayedGateAuditService extends StageGateService {
  _DelayedGateAuditService(this._pending);
  final Completer<StageGateAuditModel?> _pending;

  @override
  Future<StageGateAuditModel?> auditStageReadiness({
    required dynamic projectId,
    dynamic workspaceId,
    dynamic stagePolicyId,
    String? targetStage,
  }) =>
      _pending.future;

  @override
  Future<List<PrematureAlertModel>> getGuardrailAlerts(dynamic projectId) async =>
      const [];
}

class _DelayedTwelveWyService extends TwelveWyService {
  _DelayedTwelveWyService(this._pending);
  final Completer<TwelveWyDashboardModel?> _pending;

  @override
  Future<TwelveWyDashboardModel?> getDashboard(dynamic projectId) =>
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

  Future<SessionController> putSwitchableSession() async {
    return Get.put<SessionController>(
      SessionController(contextService: _SucceedingContextService()),
    );
  }

  test(
      'loadEvidenceData() discards a stale in-flight response after workspace switch (generation guard)',
      () async {
    final session = await putSwitchableSession();
    final pendingOld = Completer<List<HypothesisModel>>();
    final hub = HologramHubController(
      evidenceService: _DelayedEvidenceService(pendingOld),
    );

    final staleLoad = hub.loadEvidenceData(42);
    await Future<void>.delayed(Duration.zero);
    expect(hub.hypothesesList, isEmpty);

    final activation = await session.activateWorkspace('workspace-b');
    expect(activation.isSuccess, isTrue);

    pendingOld.complete([
      HypothesisModel.fromJson({'id': 1, 'statement': 'workspace-a stale hypothesis'}),
    ]);
    await staleLoad;

    expect(
      hub.hypothesesList,
      isEmpty,
      reason: 'response trả về SAU khi workspace đã chuyển phải bị bỏ qua',
    );
  });

  test(
      'loadEvidenceData() still writes the response when the generation has NOT changed',
      () async {
    await putSwitchableSession();
    final pending = Completer<List<HypothesisModel>>();
    final hub = HologramHubController(
      evidenceService: _DelayedEvidenceService(pending),
    );

    final load = hub.loadEvidenceData(42);
    await Future<void>.delayed(Duration.zero);
    pending.complete([
      HypothesisModel.fromJson({'id': 2, 'statement': 'workspace-a fresh hypothesis'}),
    ]);
    await load;

    expect(hub.hypothesesList, hasLength(1));
    expect(hub.hypothesesList.first.statement, 'workspace-a fresh hypothesis');
  });

  test(
      'loadStageLensesData() discards a stale in-flight response after workspace switch (generation guard)',
      () async {
    final session = await putSwitchableSession();
    final pendingOld = Completer<StageLensSummaryModel?>();
    final hub = HologramHubController(
      lensService: _DelayedLensService(pendingOld),
    );

    final staleLoad = hub.loadStageLensesData(42);
    await Future<void>.delayed(Duration.zero);
    expect(hub.stageLensSummary.value, isNull);

    final activation = await session.activateWorkspace('workspace-b');
    expect(activation.isSuccess, isTrue);

    pendingOld.complete(
      StageLensSummaryModel.fromJson({'project_id': 999, 'project_stage': 'P2_SOLUTION_VALIDATION'}),
    );
    await staleLoad;

    expect(hub.stageLensSummary.value, isNull);
  });

  test(
      'loadStageLensesData() still writes the response when the generation has NOT changed',
      () async {
    await putSwitchableSession();
    final pending = Completer<StageLensSummaryModel?>();
    final hub = HologramHubController(lensService: _DelayedLensService(pending));

    final load = hub.loadStageLensesData(42);
    await Future<void>.delayed(Duration.zero);
    pending.complete(StageLensSummaryModel.fromJson({'project_id': 42}));
    await load;

    expect(hub.stageLensSummary.value, isNotNull);
    expect(hub.stageLensSummary.value!.projectId, 42);
  });

  test(
      'loadStageGateData() discards a stale in-flight response after workspace switch (generation guard)',
      () async {
    final session = await putSwitchableSession();
    final pendingOld = Completer<List<PrematureAlertModel>>();
    final hub = HologramHubController(
      stageGateService: _DelayedGateAlertsService(pendingOld),
    );

    final staleLoad = hub.loadStageGateData(42);
    await Future<void>.delayed(Duration.zero);
    expect(hub.prematureAlerts, isEmpty);

    final activation = await session.activateWorkspace('workspace-b');
    expect(activation.isSuccess, isTrue);

    pendingOld.complete([
      PrematureAlertModel.fromJson({'id': 1, 'current_stage': 'P1_PROBLEM_VALIDATION'}),
    ]);
    await staleLoad;

    expect(hub.prematureAlerts, isEmpty);
  });

  test(
      'loadStageGateData() still writes the response when the generation has NOT changed',
      () async {
    await putSwitchableSession();
    final pending = Completer<List<PrematureAlertModel>>();
    final hub = HologramHubController(stageGateService: _DelayedGateAlertsService(pending));

    final load = hub.loadStageGateData(42);
    await Future<void>.delayed(Duration.zero);
    pending.complete([
      PrematureAlertModel.fromJson({'id': 2, 'current_stage': 'P1_PROBLEM_VALIDATION'}),
    ]);
    await load;

    expect(hub.prematureAlerts, hasLength(1));
  });

  test(
      'runStageGateAudit() discards a stale in-flight audit result after workspace switch (generation guard)',
      () async {
    final session = await putSwitchableSession();
    final pendingOld = Completer<StageGateAuditModel?>();
    final hub = HologramHubController(
      stageGateService: _DelayedGateAuditService(pendingOld),
    );
    hub.onProjectSelected(42);

    final staleRun = hub.runStageGateAudit();
    await Future<void>.delayed(Duration.zero);
    expect(hub.latestStageAudit.value, isNull);

    final activation = await session.activateWorkspace('workspace-b');
    expect(activation.isSuccess, isTrue);

    pendingOld.complete(
      StageGateAuditModel.fromJson({'id': 1, 'to_stage': 'P2_SOLUTION_VALIDATION'}),
    );
    await staleRun;

    expect(
      hub.latestStageAudit.value,
      isNull,
      reason:
          'runStageGateAudit ghi thẳng kết quả audit (dữ liệu tenant thật) — response trễ của workspace CŨ phải bị discard',
    );
  });

  test(
      'runStageGateAudit() still writes the response when the generation has NOT changed',
      () async {
    await putSwitchableSession();
    final pending = Completer<StageGateAuditModel?>();
    final hub = HologramHubController(stageGateService: _DelayedGateAuditService(pending));
    hub.onProjectSelected(42);

    final run = hub.runStageGateAudit();
    await Future<void>.delayed(Duration.zero);
    pending.complete(StageGateAuditModel.fromJson({'id': 2, 'to_stage': 'P2_SOLUTION_VALIDATION'}));
    await run;

    expect(hub.latestStageAudit.value, isNotNull);
    expect(hub.latestStageAudit.value!.toStage, 'P2_SOLUTION_VALIDATION');
  });

  test(
      'loadTwelveWyDashboard() discards a stale in-flight response after workspace switch (generation guard)',
      () async {
    final session = await putSwitchableSession();
    final pendingOld = Completer<TwelveWyDashboardModel?>();
    final hub = HologramHubController(
      twelveWyService: _DelayedTwelveWyService(pendingOld),
    );

    final staleLoad = hub.loadTwelveWyDashboard(projectId: 42);
    await Future<void>.delayed(Duration.zero);
    expect(hub.twelveWyDashboard.value, isNull);

    final activation = await session.activateWorkspace('workspace-b');
    expect(activation.isSuccess, isTrue);

    pendingOld.complete(TwelveWyDashboardModel.fromJson({'current_week': 5}));
    await staleLoad;

    expect(hub.twelveWyDashboard.value, isNull);
  });

  test(
      'loadTwelveWyDashboard() still writes the response when the generation has NOT changed',
      () async {
    await putSwitchableSession();
    final pending = Completer<TwelveWyDashboardModel?>();
    final hub = HologramHubController(twelveWyService: _DelayedTwelveWyService(pending));

    final load = hub.loadTwelveWyDashboard(projectId: 42);
    await Future<void>.delayed(Duration.zero);
    pending.complete(TwelveWyDashboardModel.fromJson({'current_week': 3}));
    await load;

    expect(hub.twelveWyDashboard.value, isNotNull);
    expect(hub.twelveWyDashboard.value!.currentWeek, 3);
  });
}
