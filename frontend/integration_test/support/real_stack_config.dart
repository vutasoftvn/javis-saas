// Task 18 (P5) — chọn chế độ chạy cho `frontend/integration_test/*_test.dart`
// qua `--dart-define`. Đọc file này TRƯỚC khi sửa 3 test dual-mode hoặc
// `frontend/tool/run_integration_real.sh` — xem
// `docs/testing/frontend-integration.md` §Dual-mode.
//
// `E2E_MODE=fixture` (mặc định): 3 test chạy Y HỆT hôm nay — `FixtureServer`
// in-process (HTTP loopback thật, không mock `ApiClient`), KHÔNG cần backend
// thật. Đây là đường CI chặn-PR, tuyệt đối không được hồi quy.
//
// `E2E_MODE=real`: `ApiClient` trỏ vào stack 4 plane THẬT (`make dev-stack`
// khởi động với `E2E_TEST_SEED_ENABLED=1`). Seed danh tính + workspace qua
// `POST /identity/_e2e/session` trên `services/company` — đúng pattern seed kit
// Python `tests/e2e/seed/identity.py` (đường HTTP hợp lệ DUY NHẤT cấp local
// session token dùng được cho business API). `FakeSecretStore` vẫn được giữ
// (không chạm Keychain/Keystore thật) ở CẢ HAI chế độ.
library;

import 'dart:convert';

import 'package:http/http.dart' as http;

import 'package:frontend/core/network/api_client.dart';

class RealStackConfig {
  RealStackConfig._();

  /// `fixture` (mặc định) | `real`.
  static const String mode =
      String.fromEnvironment('E2E_MODE', defaultValue: 'fixture');

  static bool get isReal => mode == 'real';
  static bool get isFixture => !isReal;

  /// `services/company` (Encore/TS) — business plane. Map tới
  /// `ApiClient.setBaseUrl`. Khớp `make dev-stack` (`encore run --port=4000`).
  static const String companyUrl = String.fromEnvironment(
    'E2E_COMPANY_URL',
    defaultValue: 'http://127.0.0.1:4000',
  );

  /// `services/cosa` (Encore/TS) — control plane, phục vụ `/platform/*`. Map
  /// tới `ApiClient.setPlatformBaseUrl`. Khớp `make dev-stack`
  /// (`encore run --port=4001`).
  static const String cosaUrl = String.fromEnvironment(
    'E2E_COSA_URL',
    defaultValue: 'http://127.0.0.1:4001',
  );

  /// `apps/cosa` API (uvicorn) — AgentOS plane, phục vụ `/agent/*`. Map tới
  /// `ApiClient.setAgentOsBaseUrl`. Mặc định `:8000` khớp `make dev-stack`
  /// (`python -m apps.cosa.api.main`) — LƯU Ý khác default `:8001` của
  /// `ApiClient.agentOsBaseUrl` (docker-compose map host 8001→container 8000;
  /// `make dev-stack` bind thẳng 8000).
  static const String apiUrl = String.fromEnvironment(
    'E2E_API_URL',
    defaultValue: 'http://127.0.0.1:8000',
  );

  /// Trỏ `ApiClient` (cả 3 origin) vào stack thật. Gọi trong `setUp` của
  /// mỗi test khi [isReal]. Tương ứng với 3 lời `ApiClient.set*BaseUrl` mà
  /// `setUp` fixture-mode gọi với `fixture.origin`.
  static void pointApiClientAtRealStack() {
    ApiClient.setBaseUrl(companyUrl);
    ApiClient.setPlatformBaseUrl(cosaUrl);
    ApiClient.setAgentOsBaseUrl(apiUrl);
    ApiClient.clearRuntimeContext();
  }
}

/// Kết quả seed từ `POST /identity/_e2e/session`.
class RealSeededSession {
  const RealSeededSession({
    required this.userId,
    required this.workspaceId,
    required this.accessToken,
  });

  final String userId;
  final String workspaceId;
  final String accessToken;
}

/// Seed một danh tính + workspace THẬT (role `founder`, 1 transaction:
/// `core.user_projections` + `core.workspaces` + `core.workspace_memberships`)
/// qua `POST /identity/_e2e/session` trên `services/company`
/// (`identity/handlers/e2e-session.handler.ts`, `expose:false` nhưng gọi được
/// qua HTTP khi `E2E_TEST_SEED_ENABLED=1`). Token trả về DÙNG ĐƯỢC NGAY cho
/// business API của company (đi qua `requireWorkspaceAccess`). Xem
/// `tests/e2e/seed/identity.py::create_company_session`.
Future<RealSeededSession> seedRealCompanySession({
  String companyUrl = RealStackConfig.companyUrl,
  http.Client? client,
  String displayName = 'E2E Flutter',
}) async {
  final http.Client c = client ?? http.Client();
  try {
    // Email duy nhất mỗi lần seed — `_e2e/session` luôn tạo user + workspace
    // RIÊNG, không tái dùng state giữa các lần chạy (giống DisposableCluster
    // của Tier 1 Python).
    final suffix = DateTime.now().microsecondsSinceEpoch.toRadixString(36);
    final resp = await c.post(
      Uri.parse('$companyUrl/identity/_e2e/session'),
      headers: const {'Content-Type': 'application/json'},
      body: jsonEncode({
        'email': 'e2e-flutter-$suffix@example.test',
        'displayName': displayName,
      }),
    );
    if (resp.statusCode != 200) {
      throw StateError(
        'POST $companyUrl/identity/_e2e/session lỗi (${resp.statusCode}): '
        '${resp.body}\n'
        'Kiểm tra: (1) `make dev-stack` đang chạy, (2) stack được khởi động '
        'với `E2E_TEST_SEED_ENABLED=1` (handler trả 403 nếu thiếu biến này).',
      );
    }
    final body = jsonDecode(resp.body) as Map<String, dynamic>;
    return RealSeededSession(
      userId: body['userId'].toString(),
      workspaceId: body['workspaceId'].toString(),
      accessToken: body['accessToken'].toString(),
    );
  } finally {
    if (client == null) c.close();
  }
}
