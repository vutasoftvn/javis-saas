// Task 11 — bằng chứng release: workspace ở REMOTE_ACCESS + node OFFLINE
// phải (1) hiện banner chỉ-đọc thật (không suy diễn từ text tuỳ ý) và (2)
// KHÔNG BAO GIỜ gửi ra ngoài bất kỳ request mutation nghiệp vụ nào khi người
// dùng cố bấm hành động approve — đo trực tiếp trên wire qua `ApiRecorder`,
// không chỉ kiểm tra nút có bị disable trên UI hay không (một lỗi tương lai
// có thể vẫn để nút bấm được nhưng service tự chặn muộn — test này loại trừ
// khả năng đó bằng cách xác nhận KHÔNG có socket request nào cả).
library;

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:get/get.dart';
import 'package:http/http.dart' as http;
import 'package:integration_test/integration_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:frontend/core/network/api_client.dart';
import 'package:frontend/core/network/realtime_service.dart';
import 'package:frontend/core/runtime/mutation_gate.dart';
import 'package:frontend/core/services/secure_storage_service.dart';
import 'package:frontend/core/session/session_controller.dart';
import 'package:frontend/core/widgets/runtime_app_chrome.dart';
import 'package:frontend/modules/approvals/controllers/approvals_controller.dart';
import 'package:frontend/modules/approvals/services/approvals_service.dart';
import 'package:frontend/modules/approvals/views/approvals_view.dart';
import 'package:frontend/modules/remote_access/controllers/remote_access_controller.dart';

import 'support/api_recorder.dart';
import 'support/fake_secret_store.dart';
import 'support/fixture_server.dart';

/// Đưa session vào đúng trạng thái REMOTE_ACCESS+OFFLINE bằng CHÍNH đường đi
/// production thật (`SessionController.activateWorkspace` — không tự gán
/// field runtime bằng tay) để `ApiClient.runtimeMode/nodePresence` VÀ
/// `RemoteAccessController.status` đồng bộ đúng như app thật (cả hai đều do
/// `SessionController._commit` set trong cùng một khối, xem
/// `session_controller.dart`).
Future<void> enterRemoteOfflineWorkspace(
  SessionController session,
  FixtureServer fixture,
) async {
  await SecureStorageService.write('local_session_token', 'seed-remote-offline-token');
  final result = await session.activateWorkspace('workspace-remote-offline');
  if (!result.isSuccess) {
    fail('failed to seed remote-offline workspace: ${result.failureMessage}');
  }
}

void main() {
  IntegrationTestWidgetsFlutterBinding.ensureInitialized();

  late FixtureServer fixture;
  late ApiRecorder apiRecorder;
  late SessionController session;
  late RemoteAccessController remoteAccess;

  setUp(() async {
    Get.testMode = true;
    SharedPreferences.setMockInitialValues({});
    SecureStorageService.configureForTest(FakeSecretStore());

    fixture = FixtureServer(
      platformToken: 'unused-platform-token',
      localSessionToken: 'unused-local-token',
      workspaces: const [
        FixtureWorkspace(
          workspaceId: 'workspace-remote-offline',
          name: 'Remote Offline Workspace',
          runtimeMode: 'REMOTE_ACCESS',
          runtimeModeSource: 'configured',
          presenceStatus: 'OFFLINE',
        ),
      ],
      approvals: [fixtureApprovalJson(id: 'appr-remote-1')],
    );
    await fixture.start();

    apiRecorder = ApiRecorder();
    ApiClient.client = apiRecorder.wrap(http.Client());
    ApiClient.setBaseUrl(fixture.origin);
    ApiClient.setPlatformBaseUrl(fixture.origin);
    ApiClient.setAgentOsBaseUrl(fixture.origin);
    ApiClient.clearRuntimeContext();

    session = Get.put(SessionController(), permanent: true);
    remoteAccess = Get.put(RemoteAccessController(), permanent: true);
  });

  tearDown(() async {
    // Không gọi `session.logout()` ở đây: nó điều hướng
    // `Get.offAllNamed(AppRoutes.login)`, đòi hỏi route table đã đăng ký —
    // widget đã bị `Get.reset()` tháo dỡ ngay sau test này. Chỉ cần dừng
    // đúng side effect có thể rò rỉ sang test sau: Timer reconnect SSE thật.
    RealtimeService().stop(clearCheckpoint: true);
    await fixture.stop();
    Get.reset();
    SecureStorageService.resetForTest();
  });

  testWidgets(
    'remote offline shows read-only and sends no approval mutation',
    (tester) async {
      await enterRemoteOfflineWorkspace(session, fixture);
      expect(remoteAccess.isOffline, isTrue);

      final approvalsHttpClient = apiRecorder.wrap(http.Client());
      Get.put(
        ApprovalsController(
          mutationGate: SessionMutationGate(sessionController: session),
          approvalsService: ApprovalsService(httpClient: approvalsHttpClient),
        ),
      );

      await tester.pumpWidget(
        GetMaterialApp(
          home: RuntimeAppChrome(child: ApprovalsView()),
        ),
      );
      await tester.pumpAndSettle();

      // (1) Banner chỉ-đọc thật — không suy diễn, đọc trực tiếp từ
      // `RuntimeStatus.bannerMessage` (runtime_status.dart) qua widget tree.
      expect(find.textContaining('chỉ đọc'), findsWidgets);

      // (2) Nút phê duyệt phải bị vô hiệu hoá TRƯỚC khi bấm (Task 5 —
      // control tự disable, không đợi bấm rồi báo lỗi sau).
      final approveButtonFinder = find.widgetWithText(ElevatedButton, 'Chấp thuận (Approve)');
      expect(approveButtonFinder, findsOneWidget);
      final approveButton = tester.widget<ElevatedButton>(approveButtonFinder);
      expect(approveButton.onPressed, isNull);

      // Vẫn "bấm" (đúng bước brief mô tả) — trên nút đã disable, đây là no-op
      // ở tầng Flutter, không có gì được gửi ra ngoài.
      await tester.tap(approveButtonFinder, warnIfMissed: false);
      await tester.pumpAndSettle();

      // (3) Đo trực tiếp trên wire: không một request mutation nghiệp vụ nào
      // (POST/PUT/PATCH/DELETE ngoài bootstrap) từng được gửi đi.
      expect(apiRecorder.businessPosts, isEmpty);
    },
  );
}
