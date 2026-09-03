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
//
// Task 18 — dual-mode. `E2E_MODE=fixture` (mặc định): y hệt hôm nay (login qua
// `FixtureServer` + widget picker + `SessionController.activateWorkspace`).
// `E2E_MODE=real`: `SessionController.activateWorkspace` KHÔNG chạy được vì hop
// `GET services/cosa /platform/workspaces/:id/session-context` yêu cầu platform
// token (`PLATFORM_JWT_SECRET`) mà seed `_e2e/session` không cấp — đây là bug
// B5 (`ADR-COSA-DELEGATION-002`, PROPOSED). Nhánh real vì vậy chứng minh CÙNG
// một tuyên bố wire-level ("sau khi chuyển workspace, không request nào mang
// `X-Workspace-Id` của tenant cũ") nhưng ở tầng transport `ApiClient` thật
// chống lại `services/company` THẬT (B5-independent). Đường controller/widget
// đầy đủ trong real mode chờ B5.
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
import 'support/real_stack_config.dart';

/// Nhánh `E2E_MODE=real` — tenant-header isolation ở tầng transport thật
/// chống lại `services/company` THẬT, KHÔNG phụ thuộc cosa (B5-independent).
///
/// Mô phỏng đúng bất biến mà `SessionController._commit` phải giữ: sau khi
/// "chuyển" sang workspace B (đổi `local_session_token` + `workspace_id` trong
/// secure storage — chính là 2 key `ApiClient._getHeaders` đọc), MỌI request
/// tiếp theo chỉ được mang `X-Workspace-Id` của B.
Future<void> _runRealTenantIsolation(
  WidgetTester tester,
  ApiRecorder apiRecorder,
) async {
  final wsA = await seedRealCompanySession(displayName: 'E2E Owner A');
  final wsB = await seedRealCompanySession(displayName: 'E2E Owner B');
  expect(wsA.workspaceId == wsB.workspaceId, isFalse,
      reason: '_e2e/session phải cấp workspace riêng mỗi lần seed');

  // Ngữ cảnh workspace A.
  await SecureStorageService.write('local_session_token', wsA.accessToken);
  await SecureStorageService.write('workspace_id', wsA.workspaceId);
  final meA = await ApiClient.get('/identity/me');
  expect(meA.statusCode, 200, reason: 'founder A đọc /identity/me: ${meA.body}');
  expect(apiRecorder.workspaceHeaders, everyElement(wsA.workspaceId));

  // Chỉ tính rò rỉ cho request TỪ SAU thời điểm chuyển.
  apiRecorder.clear();

  // "Chuyển" sang workspace B — đổi đúng 2 key mà transport đọc.
  await SecureStorageService.write('local_session_token', wsB.accessToken);
  await SecureStorageService.write('workspace_id', wsB.workspaceId);

  final meB = await ApiClient.get('/identity/me');
  expect(meB.statusCode, 200, reason: 'founder B đọc /identity/me: ${meB.body}');
  // Một request business bất kỳ khác cũng phải mang đúng tenant mới.
  await ApiClient.get('/operations/tasks');

  expect(apiRecorder.workspaceHeaders, isNotEmpty);
  expect(apiRecorder.workspaceHeaders, everyElement(wsB.workspaceId));
}

void main() {
  IntegrationTestWidgetsFlutterBinding.ensureInitialized();

  FixtureServer? fixture;
  late ApiRecorder apiRecorder;

  setUp(() async {
    Get.testMode = true;
    SharedPreferences.setMockInitialValues({});
    SecureStorageService.configureForTest(FakeSecretStore());

    apiRecorder = ApiRecorder();
    ApiClient.client = apiRecorder.wrap(http.Client());

    if (RealStackConfig.isReal) {
      RealStackConfig.pointApiClientAtRealStack();
      return;
    }

    final f = FixtureServer(
      platformToken: 'platform-token-member-a',
      localSessionToken: 'local-token-member-a',
      workspaces: const [
        FixtureWorkspace(workspaceId: 'workspace-a', name: 'Workspace A'),
        FixtureWorkspace(workspaceId: 'workspace-b', name: 'Workspace B'),
      ],
    );
    await f.start();
    fixture = f;

    ApiClient.setBaseUrl(f.origin);
    ApiClient.setPlatformBaseUrl(f.origin);
    ApiClient.setAgentOsBaseUrl(f.origin);
    ApiClient.clearRuntimeContext();
  });

  tearDown(() async {
    // Thứ tự bắt buộc: dừng SSE reconnect loop (Timer thật, xem
    // `RealtimeService`) TRƯỚC khi đóng fixture server — nếu đảo ngược, một
    // lần reconnect trễ có thể bắn request tới cổng đã đóng, ném lỗi rơi
    // ngoài test hiện tại và làm nhiễu test tiếp theo.
    RealtimeService().stop(clearCheckpoint: true);
    await fixture?.stop();
    fixture = null;
    Get.reset();
    SecureStorageService.resetForTest();
  });

  testWidgets(
    'switch workspace never leaves data from the previous tenant',
    (tester) async {
      if (RealStackConfig.isReal) {
        await _runRealTenantIsolation(tester, apiRecorder);
        return;
      }

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
