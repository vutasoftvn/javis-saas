// Fix-review (2026-09-02, final review C-1) — Task 9 đăng ký
// `HologramHubController`/`FounderCommandCenterController` với
// `Get.put(..., permanent: true)` tại `AppShellController.ensureShellDependencies`,
// nghĩa là hai controller này KHÔNG bị Get huỷ khi logout/chuyển workspace
// (khác trước Task 9, khi chúng nằm sau `DashboardBinding`/`HologramHubBinding`
// dạng lazyPut, tự dispose theo `Get.offAllNamed(login)`). Không có bước dọn
// dẹp tường minh, dữ liệu tenant CŨ (approvals/pulse/escalations/work
// products/conversation id...) tiếp tục hiển thị cho tenant MỚI — một rò rỉ
// cách ly tenant thật sự, không chỉ là "dữ liệu cũ vô hại". Test này chứng
// minh `SessionController.activateWorkspace`/`logout` gọi đúng
// `resetForWorkspace()` trên cả hai controller.
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
import 'package:frontend/data/models/founder_decision_model.dart';
import 'package:frontend/modules/auth/services/auth_service.dart';
import 'package:frontend/modules/hologram_hub/controllers/founder_command_center_controller.dart';
import 'package:frontend/modules/hologram_hub/controllers/hologram_hub_controller.dart';
import 'package:frontend/modules/workforce/models/workforce_mvp_models.dart';

import '../services/fakes/fake_secret_store.dart';

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

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  Get.testMode = true;

  late http.Client originalClient;

  setUp(() {
    SharedPreferences.setMockInitialValues({'workspace_id': 'workspace-a'});
    SecureStorageService.configureForTest(FakeSecretStore());
    AuthService.setCachedToken('fake-token-for-shell-reset-test');
    originalClient = ApiClient.client;
    // Mọi request nền phát sinh bởi resetForWorkspace()'s reload (loadHubSummary/
    // listApprovals/pulse/...) chỉ cần trả 200 rỗng — test này không quan tâm
    // dữ liệu nghiệp vụ mới, chỉ quan tâm dữ liệu CŨ có bị xoá hay không.
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

  group('SessionController.activateWorkspace resets permanent shell controllers', () {
    test(
        'HologramHubController + FounderCommandCenterController tenant state is cleared for the new workspace',
        () async {
      final hub = Get.put<HologramHubController>(HologramHubController());
      final fcc = Get.put<FounderCommandCenterController>(FounderCommandCenterController());

      // Seed dữ liệu tenant CŨ (workspace-a) trực tiếp vào Rx state — mô
      // phỏng đúng những gì reviewer nêu: pulse/top3Actions/pendingDecisions/
      // pendingApprovals/workforcePacks (FCC) và openEscalations/workProducts/
      // control-plane approvals (HologramHub).
      hub.pendingApprovals.add(_fakeWorkforceApproval());
      hub.openEscalations.add({'id': 1, 'title': 'workspace-a escalation'});
      hub.workProducts.add({'id': 1, 'title': 'workspace-a work product'});
      hub.controlPlaneSummary.value = {'workspace': 'workspace-a'};

      fcc.pendingDecisions.add(_fakeFounderDecision());
      fcc.pendingApprovals.add({'id': 'appr-a', 'title': 'workspace-a approval'});
      fcc.chatMessages.add({'role': 'user', 'content': 'hello from workspace-a'});
      fcc.seedConversationIdForTest('conversation-workspace-a');

      final session = SessionController(contextService: _SucceedingContextService());

      final result = await session.activateWorkspace('workspace-b');

      expect(result.isSuccess, isTrue);

      // Dữ liệu tenant CŨ phải bị xoá NGAY LẬP TỨC (đồng bộ, trong cùng
      // _commit) — không chờ tới lần reload/timer kế tiếp.
      expect(hub.pendingApprovals, isEmpty);
      expect(hub.openEscalations, isEmpty);
      expect(hub.workProducts, isEmpty);
      expect(hub.controlPlaneSummary.value, isNull);

      expect(fcc.pendingDecisions, isEmpty);
      expect(fcc.pendingApprovals, isEmpty);
      expect(fcc.chatMessages, isEmpty);
      expect(
        fcc.cofounderConversationIdForTest,
        isNull,
        reason: 'conversation id của workspace CŨ không được rò rỉ sang workspace MỚI',
      );
    });
  });

  group('SessionController.logout clears permanent shell controllers', () {
    test('HologramHubController + FounderCommandCenterController tenant state is cleared on logout',
        () async {
      final hub = Get.put<HologramHubController>(HologramHubController());
      final fcc = Get.put<FounderCommandCenterController>(FounderCommandCenterController());

      hub.pendingApprovals.add(_fakeWorkforceApproval());
      fcc.pendingDecisions.add(_fakeFounderDecision());
      fcc.seedConversationIdForTest('conversation-workspace-a');

      final session = SessionController(
        contextService: _SucceedingContextService(),
        navigateToLogin: () {}, // không cần điều hướng thật trong test
      );
      session.seedForTest(_snapshotFor('workspace-a'));

      await session.logout();

      expect(hub.pendingApprovals, isEmpty);
      expect(fcc.pendingDecisions, isEmpty);
      expect(fcc.cofounderConversationIdForTest, isNull);
    });
  });
}

WorkforceApproval _fakeWorkforceApproval() => WorkforceApproval(
      approvalId: 'appr-a',
      runId: 'run-a',
      action: 'send_email',
      subject: 'workspace-a agent',
      status: 'PENDING',
      riskLevel: 'HIGH',
      requiredRole: 'founder',
      policyId: 'policy-a',
      createdAt: DateTime.utc(2026, 9, 1),
    );

FounderDecisionModel _fakeFounderDecision() => FounderDecisionModel(
      id: 1,
      domain: 'strategy',
      question: 'Should we pivot?',
      status: 'PENDING',
      createdAt: DateTime.utc(2026, 9, 1),
    );
