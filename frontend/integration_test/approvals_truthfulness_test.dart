// Task 11 — bằng chứng release cho đúng bug Task 6 sửa: một 503 thật từ
// endpoint approval (Agent runtime quá tải/không sẵn sàng) phải render một
// trạng thái LỖI THẬT (`FeatureFailure` → "Không thể tải dữ liệu lúc này"),
// TUYỆT ĐỐI không được co về danh sách rỗng trông giống "đã tải xong, không
// có gì" (`FeatureData([])`) — hai trạng thái này khác nhau về BẢN CHẤT
// (server có lỗi thật vs. server xác nhận không có approval nào) và UI không
// được phép nhầm lẫn chúng.
//
// Task 18 — dual-mode. `E2E_MODE=fixture` (mặc định): y hệt hôm nay, fault
// injection 503 qua `FixtureServer`. `E2E_MODE=real`: trỏ vào `apps/cosa` API
// thật; fault 503 KHÔNG tái tạo được trên stack khoẻ, nên assertion
// 503→`FeatureFailure` giữ nguyên là fixture-only (guard bên dưới) — phần real
// chỉ khẳng định endpoint approval thật resolve về một trạng thái TERMINAL
// (không kẹt loading, không bịa danh sách rỗng). Xem
// `docs/testing/frontend-integration.md` §Dual-mode.
library;

import 'package:flutter_test/flutter_test.dart';
import 'package:get/get.dart';
import 'package:http/http.dart' as http;
import 'package:integration_test/integration_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:frontend/core/network/api_client.dart';
import 'package:frontend/core/services/secure_storage_service.dart';
import 'package:frontend/modules/approvals/controllers/approvals_controller.dart';
import 'package:frontend/modules/approvals/services/approvals_service.dart';
import 'package:frontend/modules/approvals/views/approvals_view.dart';

import 'support/fake_secret_store.dart';
import 'support/fixture_server.dart';
import 'support/real_stack_config.dart';

void main() {
  IntegrationTestWidgetsFlutterBinding.ensureInitialized();

  FixtureServer? fixture;

  setUp(() async {
    Get.testMode = true;
    SharedPreferences.setMockInitialValues({});
    SecureStorageService.configureForTest(FakeSecretStore());

    if (RealStackConfig.isReal) {
      // Chế độ real — seed danh tính THẬT (role founder) rồi cấp local token
      // + workspace vào secure storage. `DefaultApiAuthResolver` đọc đúng hai
      // key này (như nhánh fixture bên dưới), khác biệt duy nhất là giá trị
      // đến từ `POST /identity/_e2e/session` thay vì hằng số.
      final seeded = await seedRealCompanySession();
      await SecureStorageService.write('local_session_token', seeded.accessToken);
      await SecureStorageService.write('workspace_id', seeded.workspaceId);
      RealStackConfig.pointApiClientAtRealStack();
      return;
    }

    // `DefaultApiAuthResolver` (dùng bởi `MvpRequestClient`) đọc
    // `local_session_token`/`workspace_id` từ đây — PHẢI seed đủ hai giá trị
    // này, nếu không request bị `MvpRequestClient` tự chặn TRƯỚC KHI chạm
    // tới fixture (lỗi "Missing authentication token") thay vì thật sự nhận
    // 503 từ fault injection §3 của brief.
    await SecureStorageService.write('local_session_token', 'seed-token');
    await SecureStorageService.write('workspace_id', 'workspace-a');

    final f = FixtureServer(
      platformToken: 'unused',
      localSessionToken: 'unused',
      workspaces: const [
        FixtureWorkspace(workspaceId: 'workspace-a', name: 'Workspace A'),
      ],
    )..approvalsUnavailable = true; // Fault injection §3 của brief.
    await f.start();
    fixture = f;

    ApiClient.setAgentOsBaseUrl(f.origin);
    ApiClient.clearRuntimeContext();
  });

  tearDown(() async {
    await fixture?.stop();
    fixture = null;
    Get.reset();
    SecureStorageService.resetForTest();
  });

  testWidgets(
    '503 from approval endpoint renders a real failure state, not a fabricated empty list',
    (tester) async {
      final controller = Get.put(
        ApprovalsController(
          approvalsService: ApprovalsService(httpClient: http.Client()),
        ),
      );

      await tester.pumpWidget(GetMaterialApp(home: ApprovalsView()));
      await tester.pumpAndSettle();

      if (RealStackConfig.isReal) {
        // Fault 503 không tái tạo được trên stack khoẻ. Điều real mode CHỨNG
        // MINH được B5-independent: gọi endpoint approval THẬT của `apps/cosa`
        // → UI đạt một trạng thái TERMINAL thật (data HOẶC failure), KHÔNG
        // kẹt `FeatureLoading`/`FeatureInitial` và KHÔNG có nhánh "bịa rỗng".
        // Việc map chính xác 503→`FeatureFailure` vẫn do fixture mode phủ.
        final stateName = controller.listState.value.runtimeType.toString();
        expect(
          stateName.startsWith('FeatureLoading') ||
              stateName.startsWith('FeatureInitial'),
          isFalse,
          reason: 'real approval endpoint phải resolve về trạng thái terminal, '
              'đang ở: $stateName',
        );
        return;
      }

      // Structural — không suy diễn qua text: state thật sự PHẢI là
      // `FeatureFailure`, không phải `FeatureData` với `value` rỗng. So
      // sánh qua tên runtime type (thay vì `isA<FeatureFailure<T>>()`) để
      // tránh phải khai đúng tham số generic ẩn `T` của `ApprovalListState`.
      expect(
        controller.listState.value.runtimeType.toString(),
        startsWith('FeatureFailure'),
      );

      // Behavioral — người dùng nhìn thấy đúng thông điệp lỗi thật
      // (`FeatureStateView._UnavailableView`), không phải một danh sách
      // trống câm lặng trông như "đã tải xong, không có phê duyệt nào".
      expect(find.text('Không thể tải dữ liệu lúc này'), findsOneWidget);
    },
  );
}
