// Task 11 — bằng chứng release: đăng nhập → chọn workspace A → chuyển sang
// workspace B → khẳng định KHÔNG còn request nào rò rỉ `X-Workspace-Id` của
// workspace A. Đây là lát cắt "truthful MVP" cốt lõi của cả kế hoạch 11 task
// (Task 4 — SessionController transaction) chạy qua widget tree THẬT, HTTP
// THẬT (loopback tới `FixtureServer`, không mock `ApiClient`), không chỉ unit
// test controller cô lập.
//
// Fixture: xem `docs/testing/frontend-integration.md` §Fixture data — user
// "member-a", hai workspace "workspace-a"/"workspace-b" cùng LOCAL_ONLY/ONLINE
// (không dính tới runtime offline — đó là phạm vi của
// `remote_access_flow_test.dart`).
library;

import 'package:flutter_test/flutter_test.dart';
import 'package:get/get.dart';
import 'package:http/http.dart' as http;
import 'package:integration_test/integration_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:frontend/core/network/api_client.dart';
import 'package:frontend/core/network/realtime_service.dart';
import 'package:frontend/core/routing/app_pages.dart';
import 'package:frontend/core/routing/app_routes.dart';
import 'package:frontend/core/services/secure_storage_service.dart';
import 'package:frontend/core/session/session_binding.dart';
import 'package:frontend/core/session/session_controller.dart';
import 'package:frontend/modules/auth/services/auth_service.dart';
import 'package:frontend/modules/workspace_picker/bindings/workspace_picker_binding.dart';
import 'package:frontend/modules/workspace_picker/views/workspace_picker_view.dart';

import 'support/api_recorder.dart';
import 'support/fake_secret_store.dart';
import 'support/fixture_server.dart';

void main() {
  IntegrationTestWidgetsFlutterBinding.ensureInitialized();

  late FixtureServer fixture;
  late ApiRecorder apiRecorder;

  setUp(() async {
    Get.testMode = true;
    SharedPreferences.setMockInitialValues({});
    SecureStorageService.configureForTest(FakeSecretStore());

    fixture = FixtureServer(
      platformToken: 'platform-token-member-a',
      localSessionToken: 'local-token-member-a',
      workspaces: const [
        FixtureWorkspace(workspaceId: 'workspace-a', name: 'Workspace A'),
        FixtureWorkspace(workspaceId: 'workspace-b', name: 'Workspace B'),
      ],
    );
    await fixture.start();

    apiRecorder = ApiRecorder();
    ApiClient.client = apiRecorder.wrap(http.Client());
    ApiClient.setBaseUrl(fixture.origin);
    ApiClient.setPlatformBaseUrl(fixture.origin);
    ApiClient.setAgentOsBaseUrl(fixture.origin);
    ApiClient.clearRuntimeContext();
  });

  tearDown(() async {
    // Thứ tự bắt buộc: dừng SSE reconnect loop (Timer thật, xem
    // `RealtimeService`) TRƯỚC khi đóng fixture server — nếu đảo ngược, một
    // lần reconnect trễ có thể bắn request tới cổng đã đóng, ném lỗi rơi
    // ngoài test hiện tại và làm nhiễu test tiếp theo.
    RealtimeService().stop(clearCheckpoint: true);
    await fixture.stop();
    Get.reset();
    SecureStorageService.resetForTest();
  });

  testWidgets(
    'switch workspace never leaves data from the previous tenant',
    (tester) async {
      await tester.pumpWidget(
        GetMaterialApp(
          initialRoute: AppRoutes.login,
          getPages: AppPages.routes,
          initialBinding: SessionBinding(),
        ),
      );
      await tester.pumpAndSettle();

      // Gọi thẳng `AuthService` thật (cùng 2 bước production —
      // loginPlatform → syncFromPlatform — mà `AuthController.login()` gọi
      // bên trong) thay vì đi qua controller: điều hướng sau khi
      // `Get.toNamed`/`Get.offAllNamed` được gọi fire-and-forget bên trong
      // `login()` phụ thuộc lịch trình microtask nội bộ của GetX, không có
      // seam để test chờ đúng thời điểm mà không phải chờ mù (sleep) — gọi
      // trực tiếp AuthService rồi TỰ điều hướng ở đây cho kết quả tất định,
      // vẫn là đúng business logic thật (không phải service giả).
      final authService = AuthService();
      final loginResult = await authService.loginPlatform(
        'member-a@fixture.test',
        'irrelevant-password',
      );
      expect(loginResult.success, isTrue, reason: loginResult.errorMessage);

      final syncResult = await authService.syncFromPlatform(
        platformToken: loginResult.token!,
      );
      expect(syncResult.success, isTrue, reason: syncResult.errorMessage);
      expect(syncResult.workspaces, hasLength(2));

      // `Get.to` (không phải `Get.toNamed`) — điều hướng tới ĐÚNG view/
      // binding thật của route picker nhưng KHÔNG qua bảng route đặt tên
      // (`getPages`), nên không chạm `AuthMiddleware`/
      // `WorkspacePickerGuardMiddleware` (2 middleware này đọc lại
      // `Get.arguments` qua pipeline redirect riêng của named-route, không
      // phải trọng tâm của test này — trọng tâm là hành vi
      // `WorkspacePickerController.selectWorkspace`/`SessionController.
      // activateWorkspace` thật). `Get.offAllNamed(AppRoutes.hub)` mà
      // `selectWorkspace` gọi bên trong VẪN là named-route thật, đi qua
      // đúng `getPages`/`AuthMiddleware` như app thật.
      Get.to(
        () => const WorkspacePickerView(),
        binding: WorkspacePickerBinding(),
        arguments: {
          'platformToken': loginResult.token,
          'workspaces': syncResult.workspaces,
        },
      );
      await tester.pumpAndSettle();

      expect(find.text('Workspace A'), findsOneWidget);

      await tester.tap(find.text('Workspace A'));
      // KHÔNG dùng `pumpAndSettle()` từ đây: Hub thật (`DashboardView`) có
      // animation liên tục (vd. `FloatingVoiceHologram`) không bao giờ tự
      // "settle" — pumpAndSettle sẽ treo rất lâu (đã đo thực tế: ~2 phút40s)
      // trước khi timeout. Chỉ cần đủ số frame để `Get.offAllNamed`/Rx state
      // hoàn tất, không cần chờ hết animation.
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 300));
      await tester.pump(const Duration(milliseconds: 300));

      final session = Get.find<SessionController>();
      expect(session.active.value?.workspaceId, 'workspace-a');
      expect(Get.currentRoute, AppRoutes.hub);

      // Chỉ tính "rò rỉ tenant cũ" cho các request xảy ra TỪ THỜI ĐIỂM chuyển
      // sang workspace B trở đi — request của chính workspace A (hợp lệ, xảy
      // ra TRƯỚC khi chuyển) không phải là rò rỉ.
      apiRecorder.clear();

      // Chuyển workspace: production code gọi thẳng
      // `SessionController.activateWorkspace` (đây chính là API chuyển
      // workspace canonical — Task 4; picker/login đều đi qua đúng hàm này,
      // không có đường tắt nào khác trong app thật).
      final result = await session.activateWorkspace('workspace-b');
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 300));

      expect(result.isSuccess, isTrue, reason: result.failureMessage);
      expect(session.active.value?.workspaceId, 'workspace-b');

      expect(apiRecorder.workspaceHeaders, isNotEmpty);
      expect(apiRecorder.workspaceHeaders, everyElement('workspace-b'));
    },
  );
}
