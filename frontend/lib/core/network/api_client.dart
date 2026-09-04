import 'dart:convert';
import 'package:http/http.dart' as http;
import '../services/secure_storage_service.dart';

/// M5 §5 — ném ra khi `_offlineGuard` chặn một request business (REMOTE_ACCESS +
/// node OFFLINE). Các transport primitive dùng chung (SSE/multipart/form) không
/// thể trả `http.Response` 503 tổng hợp như get/post JSON (một số caller cần một
/// tín hiệu lỗi rõ ràng thay vì đọc statusCode của response), nên bọc lại thành
/// exception mang theo response 503 gốc để caller vẫn đọc được `message`.
class ApiOfflineException implements Exception {
  ApiOfflineException(this.response);

  final http.Response response;

  @override
  String toString() => 'ApiOfflineException: ${response.statusCode} ${response.body}';
}

/// Task 2 — kết quả thuần của resolver transport: hoặc có [uri] đã resolve
/// đúng plane/relay để caller tự gửi request, hoặc có [blockedResponse] (503
/// tổng hợp từ offline guard) khi request business bị chặn — hai trường hợp
/// loại trừ lẫn nhau, không bao giờ cả hai cùng null hoặc cùng non-null.
class ApiRequestTarget {
  const ApiRequestTarget({this.uri, this.blockedResponse});

  final Uri? uri;
  final http.Response? blockedResponse;
}

class ApiClient {
  static const String _configuredBaseUrl = String.fromEnvironment('API_BASE_URL');
  static String? _customBaseUrl;

  static const String _configuredPlatformBaseUrl = String.fromEnvironment('PLATFORM_BASE_URL');
  static String? _customPlatformBaseUrl;

  static const String _configuredAgentOsUrl = String.fromEnvironment('AGENTOS_BASE_URL');
  static String? _customAgentOsUrl;

  static const String _configuredDesktopWorkerUrl = String.fromEnvironment('DESKTOP_WORKER_BASE_URL');
  static String? _customDesktopWorkerUrl;

  static const String _configuredRelayBaseUrl = String.fromEnvironment('RELAY_BASE_URL');
  static String? _customRelayBaseUrl;

  /// M5 §5/§6 — runtime context được `RemoteAccessController` bơm vào sau khi
  /// login / switch workspace. `runtimeMode` quyết định business traffic đi
  /// thẳng local (`LOCAL_ONLY`) hay qua secure relay (`REMOTE_ACCESS`).
  /// `nodePresence == 'OFFLINE'` trong `REMOTE_ACCESS` ⇒ chặn request business,
  /// trả 503 tổng hợp (KHÔNG âm thầm chạy nơi khác — guardrail 7).
  /// Fix-review (2026-09-02, final review I-1) — quyết định routing ở
  /// `resolveUri`/`_offlineGuard` bên dưới đọc THẲNG `runtimeMode` này, không
  /// biết (và không cần biết) `modeSource` đi kèm nó là "configured" hay
  /// "inferred" (`SessionRuntimeInfo.modeSource`,
  /// `workspace-settings.service.ts` hard-code 'inferred' hôm nay — chưa có
  /// adapter đọc canonical config thật từ `services/company`). Nghĩa là một
  /// giá trị `REMOTE_ACCESS`/`LOCAL_ONLY` SUY ĐOÁN sai vẫn điều khiển việc gửi
  /// business request đi thẳng hay qua relay — `MutationGate` (`mutation_
  /// gate.dart`) là tuyến phòng thủ duy nhất chặn mutation ở tầng gate cho
  /// case suy đoán này (`confirmDegraded`), nhưng KHÔNG chặn ở tầng transport
  /// vì ApiClient không có khái niệm `modeSource`. Không redesign routing ở
  /// đây (cần adapter cosa→company thật, ngoài phạm vi fix frontend) — chỉ
  /// ghi chú lại rủi ro đã biết để không ai lầm tưởng route này đã được xác
  /// minh an toàn.
  static String? runtimeMode;
  static String? nodePresence;

  static void setRuntimeContext({String? mode, String? presence}) {
    runtimeMode = mode;
    nodePresence = presence;
  }

  static void clearRuntimeContext() {
    runtimeMode = null;
    nodePresence = null;
  }

  static void setBaseUrl(String url) {
    _customBaseUrl = url;
  }

  static void setRelayBaseUrl(String url) {
    _customRelayBaseUrl = url;
  }

  static void setPlatformBaseUrl(String url) {
    _customPlatformBaseUrl = url;
  }

  static void setAgentOsBaseUrl(String url) {
    _customAgentOsUrl = url;
  }

  static void setDesktopWorkerBaseUrl(String url) {
    _customDesktopWorkerUrl = url;
  }

  /// Base API URL for Local Company Microservices. Defaults to `http://127.0.0.1:4000`.
  static String get baseUrl {
    if (_customBaseUrl != null && _customBaseUrl!.isNotEmpty) return _customBaseUrl!;
    if (_configuredBaseUrl.isNotEmpty) return _configuredBaseUrl;
    return 'http://127.0.0.1:4000';
  }

  /// Base API URL for COSA Central Control Plane (Platform Identity, Companies, Licenses).
  /// Defaults to `PLATFORM_BASE_URL` env, or falls back to `http://127.0.0.1:4001`.
  static String get platformBaseUrl {
    if (_customPlatformBaseUrl != null && _customPlatformBaseUrl!.isNotEmpty) return _customPlatformBaseUrl!;
    if (_configuredPlatformBaseUrl.isNotEmpty) return _configuredPlatformBaseUrl;
    return 'http://127.0.0.1:4001';
  }

  /// Base API URL cho COSA FastAPI — "AgentOS" (AI Multi-Agent Plane), service
  /// `cosa-api` (`apps/cosa/api/routes.py`). Mặc định `http://127.0.0.1:8000`
  /// KHỚP topology dev local thật (`make dev-stack` chạy
  /// `uvicorn apps.cosa.api.main:app --port 8000` trực tiếp trên host — xem
  /// `Makefile` target `dev-stack-no-infra`). `:8001` chỉ đúng khi build trỏ
  /// vào VPS/docker-compose (`docker-compose.yml` remap host `8001:8000` cho
  /// container `cosa-api`) — môi trường đó PHẢI tự truyền
  /// `--dart-define=AGENTOS_BASE_URL=...` lúc build, không dựa vào default ở
  /// đây (giống cách README hướng dẫn truyền `API_BASE_URL`/`PLATFORM_BASE_URL`
  /// khi trỏ sang control plane đã deploy).
  ///
  /// Fix (2026-09-04) — default cũ `:8001` không khớp bất kỳ topology dev nào
  /// đang chạy thật (không docker, không remap cổng) → mọi `/agent/workforce/...`
  /// (Founder Command Center, HologramHub) luôn "Connection refused" trên máy
  /// dev mặc định, chỉ tự hoạt động nếu ai đó tình cờ tự thêm dart-define.
  static String get agentOsBaseUrl {
    if (_customAgentOsUrl != null && _customAgentOsUrl!.isNotEmpty) return _customAgentOsUrl!;
    if (_configuredAgentOsUrl.isNotEmpty) return _configuredAgentOsUrl;
    return 'http://127.0.0.1:8000';
  }

  /// Base API URL for Desktop Worker (Loopback Execution Plane). Defaults to `http://127.0.0.1:8765`.
  static String get desktopWorkerBaseUrl {
    if (_customDesktopWorkerUrl != null && _customDesktopWorkerUrl!.isNotEmpty) return _customDesktopWorkerUrl!;
    if (_configuredDesktopWorkerUrl.isNotEmpty) return _configuredDesktopWorkerUrl;
    return 'http://127.0.0.1:8765';
  }

  /// M5 §6 — Secure relay (Platform Gateway) chuyển tiếp encrypted business
  /// traffic tới remote local workspace node khi `REMOTE_ACCESS`. Không cấu hình
  /// riêng ⇒ dùng chung origin với control-plane (`platformBaseUrl`).
  static String get relayBaseUrl {
    if (_customRelayBaseUrl != null && _customRelayBaseUrl!.isNotEmpty) return _customRelayBaseUrl!;
    if (_configuredRelayBaseUrl.isNotEmpty) return _configuredRelayBaseUrl;
    return platformBaseUrl;
  }

  /// Normalizes legacy API paths to appropriate Microservice cluster routes.
  static String normalizeEndpoint(String endpoint) {
    String normalized = endpoint;
    if (normalized.startsWith('/auth/')) {
      return '/identity/${normalized.substring(6)}';
    }
    if (normalized.startsWith('/api/v1/auth/')) {
      return '/identity/${normalized.substring(13)}';
    }
    if (normalized == '/auth' || normalized == '/auth/me') {
      return '/identity/me';
    }
    if (normalized == '/api/v1/auth' || normalized == '/api/v1/auth/me') {
      return '/identity/me';
    }
    if (normalized.startsWith('/tasks')) {
      return '/operations$normalized';
    }
    if (normalized.startsWith('/api/v1/tasks')) {
      return '/operations${normalized.substring(7)}';
    }
    if (RegExp(r'^/strategy/projects/[^/]+/(stage(\?.*)?|stage/transitions(\?.*)?|next-best-actions(\?.*)?|ranked-assumptions(\?.*)?|proposed-experiments(\?.*)?)$').hasMatch(normalized)) {
      return '/operations$normalized';
    }
    if (normalized == '/strategy/projects' ||
        normalized.startsWith('/strategy/projects?') ||
        RegExp(r'^/strategy/projects/([^/?]+)(\?.*)?$').hasMatch(normalized)) {
      return '/operations/projects${normalized.substring(18)}';
    }
    if (normalized == '/api/v1/strategy/projects' ||
        normalized.startsWith('/api/v1/strategy/projects?') ||
        RegExp(r'^/api/v1/strategy/projects/([^/?]+)(\?.*)?$').hasMatch(normalized)) {
      return '/operations/projects${normalized.substring(25)}';
    }
    if (normalized.startsWith('/sales/')) {
      return '/commercial/${normalized.substring(7)}';
    }
    if (normalized.startsWith('/api/v1/sales/')) {
      return '/commercial/${normalized.substring(14)}';
    }
    if (normalized.startsWith('/finance/')) {
      return '/finance-legal/${normalized.substring(9)}';
    }
    if (normalized.startsWith('/api/v1/finance/')) {
      return '/finance-legal/${normalized.substring(16)}';
    }
    if (normalized.startsWith('/legal/')) {
      return '/finance-legal/${normalized.substring(7)}';
    }
    if (normalized.startsWith('/api/v1/legal/')) {
      return '/finance-legal/${normalized.substring(14)}';
    }
    if (normalized.startsWith('/marketing/context/')) {
      return '/commercial/marketing-context/${normalized.substring(19)}';
    }
    if (normalized == '/marketing/context' || normalized.startsWith('/marketing/context?')) {
      return '/commercial/marketing-context${normalized.substring(18)}';
    }
    if (normalized.startsWith('/api/v1/marketing/context/')) {
      return '/commercial/marketing-context/${normalized.substring(26)}';
    }
    if (normalized == '/api/v1/marketing/context' || normalized.startsWith('/api/v1/marketing/context?')) {
      return '/commercial/marketing-context${normalized.substring(25)}';
    }
    if (normalized.startsWith('/skills/')) {
      return '/agent/skills/${normalized.substring(8)}';
    }
    if (normalized == '/skills' || normalized.startsWith('/skills?')) {
      return '/agent/skills${normalized.substring(7)}';
    }
    if (normalized.startsWith('/api/v1/skills/')) {
      return '/agent/skills/${normalized.substring(15)}';
    }
    if (normalized == '/api/v1/skills' || normalized.startsWith('/api/v1/skills?')) {
      return '/agent/skills${normalized.substring(14)}';
    }
    return normalized;
  }

  /// Resolves the absolute URI based on gateway target (ControlPlane :4001, AgentOS :8000, DesktopWorker :8765, or Company Encore :4000).
  static Uri resolveUri(String endpoint) {
    String path = endpoint.trim();
    final normalized = normalizeEndpoint(path);
    if (normalized.startsWith('/platform/') || normalized == '/platform') {
      final base = Uri.parse(platformBaseUrl);
      final normalizedPath = normalized.startsWith('/') ? normalized : '/$normalized';
      return Uri.parse('${base.origin}$normalizedPath');
    }
    if (normalized.startsWith('/agent/') || normalized == '/agent' || normalized.startsWith('/agent?')) {
      final base = Uri.parse(agentOsBaseUrl);
      final normalizedPath = normalized.startsWith('/') ? normalized : '/$normalized';
      return Uri.parse('${base.origin}$normalizedPath');
    }
    if (normalized.startsWith('/local-worker/')) {
      final base = Uri.parse(desktopWorkerBaseUrl);
      final subPath = normalized.substring(13); // strip '/local-worker'
      final normalizedPath = subPath.startsWith('/') ? subPath : '/$subPath';
      return Uri.parse('${base.origin}$normalizedPath');
    }
    // Còn lại = business/local company runtime.
    final normalizedPath = normalized.startsWith('/') ? normalized : '/$normalized';
    // M5 §6 — REMOTE_ACCESS: business traffic KHÔNG tới local port trực tiếp mà đi
    // qua secure relay (Platform Gateway) tới remote local node. Token vẫn là
    // local_session_token (relay chỉ forward, không giải mã payload).
    if (runtimeMode == 'REMOTE_ACCESS') {
      final relay = Uri.parse(relayBaseUrl);
      return Uri.parse('${relay.origin}/relay$normalizedPath');
    }
    final base = Uri.parse(baseUrl);
    return Uri.parse('${base.origin}$normalizedPath');
  }

  /// M5 §6 — endpoint đi tới business/local runtime (không phải control-plane,
  /// AgentOS hay local worker).
  static bool isBusinessEndpoint(String endpoint) {
    final n = normalizeEndpoint(endpoint.trim());
    return !(n.startsWith('/platform') ||
        n.startsWith('/agent') ||
        n.startsWith('/local-worker'));
  }

  /// M5 §5 — REMOTE_ACCESS/CLOUD_CONTINUITY + node OFFLINE ⇒ trả 503 tổng hợp
  /// cho request business, KHÔNG gửi đi (không âm thầm fallback local/cloud).
  /// UI đọc mã này để hiện trạng thái offline / read-only.
  ///
  /// Fix-review (2026-09-02, final review I-4) — trước đây nhánh này chỉ nhận
  /// diện `REMOTE_ACCESS`, bỏ sót `CLOUD_CONTINUITY` (mode thứ ba có thật —
  /// `session_snapshot.dart`, `workspace-settings.service.ts`) dùng CHUNG một
  /// quy tắc với REMOTE_ACCESS trong `MutationGate._checkRelayedMutation`: cả
  /// hai đều đi qua node/relay từ xa có thể offline độc lập. Hai surface Hub
  /// (`FounderCommandCenterController`/`HubControlPlaneMixin` approve/reject)
  /// gọi service KHÔNG qua `MutationGate` — nếu tầng transport dùng chung này
  /// không tự chặn CLOUD_CONTINUITY+OFFLINE, chúng có ZERO enforcement. Sửa ở
  /// đây (điểm chốt chặn dùng chung cho MỌI caller: get/post/openSse/
  /// sendMultipart/sendForm/MvpRequestClient) thay vì vá riêng từng call site
  /// — bảo vệ cả những caller trong tương lai quên tự check gate.
  static http.Response? _offlineGuard(String endpoint) {
    final isRelayedOfflineMode =
        (runtimeMode == 'REMOTE_ACCESS' || runtimeMode == 'CLOUD_CONTINUITY') &&
            nodePresence == 'OFFLINE';
    if (isRelayedOfflineMode && isBusinessEndpoint(endpoint)) {
      return http.Response(
        jsonEncode({
          'error': 'runtime_offline',
          'message':
              'Workspace runtime node đang offline ($runtimeMode) — chỉ đọc, thử lại sau',
        }),
        503,
        headers: {'content-type': 'application/json'},
      );
    }
    return null;
  }

  /// Task 2 — transport target thuần, dùng chung cho `get/post/.../openSse/
  /// sendMultipart/sendForm` VÀ cho `MvpRequestClient` (contract-based
  /// client), tránh mỗi consumer tự ghép base URL / tự bỏ sót offline guard
  /// và timeout. Gọi lại đúng `_offlineGuard` + `resolveUri` hiện có — không
  /// nhân bản logic URL-joining ở nơi khác.
  static ApiRequestTarget resolveRequestTarget(String endpoint) {
    final blocked = _offlineGuard(endpoint);
    if (blocked != null) {
      return ApiRequestTarget(blockedResponse: blocked);
    }
    return ApiRequestTarget(uri: resolveUri(endpoint));
  }

  /// Overridable in tests (e.g. `ApiClient.client = MockClient(...)`) so
  /// services calling the static get/post/... methods below don't need
  /// their own http.Client injection point to be testable.
  static http.Client client = http.Client();

  /// M1 §1 — trust boundary: chọn token theo TARGET đã resolve, không theo text
  /// của path. CHỈ `/platform/*` (control-plane) dùng `platform_access_token`.
  /// Mọi thứ khác — local business service, local worker, VÀ `/agent/*` (AgentOS
  /// là local business runtime, verify local session token) — dùng
  /// `local_session_token`. Fallback `auth_token` cho phiên đã đăng nhập trước
  /// khi tách key (không ép logout).
  static Future<String?> _tokenForEndpoint(String endpoint) async {
    final normalized = normalizeEndpoint(endpoint.trim());
    final isPlatformTarget = normalized.startsWith('/platform');

    final primaryKey =
        isPlatformTarget ? 'platform_access_token' : 'local_session_token';
    final primary = await SecureStorageService.read(primaryKey);
    if (primary != null && primary.isNotEmpty) return primary;
    // Fallback tương thích ngược: token chung cũ.
    final legacy = await SecureStorageService.read('auth_token');
    return (legacy != null && legacy.isNotEmpty) ? legacy : null;
  }

  static Future<Map<String, String>> _getHeaders(
    String endpoint, {
    bool requiresAuth = true,
  }) async {
    final headers = {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
    };

    if (requiresAuth) {
      final token = await _tokenForEndpoint(endpoint);
      if (token != null && token.isNotEmpty) {
        headers['Authorization'] = 'Bearer $token';
      }
      final workspaceId = await SecureStorageService.read('workspace_id');
      if (workspaceId != null && workspaceId.isNotEmpty) {
        headers['X-Workspace-Id'] = workspaceId;
      }
    }

    return headers;
  }

  static const Duration defaultTimeout = Duration(seconds: 15);
  static const Duration uploadTimeout = Duration(seconds: 30);

  static Future<http.Response> get(String endpoint, {bool requiresAuth = true}) async {
    final target = resolveRequestTarget(endpoint);
    if (target.blockedResponse case final response?) return response;
    final headers = await _getHeaders(endpoint, requiresAuth: requiresAuth);
    return client.get(target.uri!, headers: headers).timeout(defaultTimeout);
  }

  static Future<http.Response> post(String endpoint, {Map<String, dynamic>? body, bool requiresAuth = true}) async {
    final target = resolveRequestTarget(endpoint);
    if (target.blockedResponse case final response?) return response;
    final headers = await _getHeaders(endpoint, requiresAuth: requiresAuth);
    return client.post(target.uri!, headers: headers, body: body != null ? jsonEncode(body) : null).timeout(defaultTimeout);
  }

  static Future<http.Response> put(String endpoint, {Map<String, dynamic>? body, bool requiresAuth = true}) async {
    final target = resolveRequestTarget(endpoint);
    if (target.blockedResponse case final response?) return response;
    final headers = await _getHeaders(endpoint, requiresAuth: requiresAuth);
    return client.put(target.uri!, headers: headers, body: body != null ? jsonEncode(body) : null).timeout(defaultTimeout);
  }

  static Future<http.Response> patch(String endpoint, {Map<String, dynamic>? body, bool requiresAuth = true}) async {
    final target = resolveRequestTarget(endpoint);
    if (target.blockedResponse case final response?) return response;
    final headers = await _getHeaders(endpoint, requiresAuth: requiresAuth);
    return client.patch(target.uri!, headers: headers, body: body != null ? jsonEncode(body) : null).timeout(defaultTimeout);
  }

  static Future<http.Response> delete(String endpoint, {bool requiresAuth = true}) async {
    final target = resolveRequestTarget(endpoint);
    if (target.blockedResponse case final response?) return response;
    final headers = await _getHeaders(endpoint, requiresAuth: requiresAuth);
    return client.delete(target.uri!, headers: headers).timeout(defaultTimeout);
  }

  /// Task 6 — SSE dùng chung resolver/offline-guard/token/`X-Workspace-Id` với
  /// get/post/... thay vì để từng service tự `Uri.parse(ApiClient.baseUrl)`.
  /// [extraHeaders] cho các trường hợp cần thêm header ngoài chuẩn (vd.
  /// `Last-Event-ID` khi resume một run event stream).
  static Future<http.StreamedResponse> openSse(
    String endpoint, {
    Map<String, String>? extraHeaders,
    bool requiresAuth = true,
  }) async {
    final target = resolveRequestTarget(endpoint);
    if (target.blockedResponse case final response?) throw ApiOfflineException(response);
    final headers = await _getHeaders(endpoint, requiresAuth: requiresAuth);
    if (extraHeaders != null) headers.addAll(extraHeaders);
    final request = http.Request('GET', target.uri!);
    request.headers.addAll(headers);
    request.headers['Accept'] = 'text/event-stream';
    return client.send(request).timeout(defaultTimeout);
  }

  /// Task 6 — multipart upload (vd. voice transcription) qua cùng
  /// resolver/offline-guard/token/`X-Workspace-Id`. `Content-Type` do
  /// `http.MultipartRequest` tự set (đè header JSON mặc định) khi `finalize()`.
  static Future<http.Response> sendMultipart(
    String endpoint, {
    Map<String, String>? fields,
    List<http.MultipartFile>? files,
    bool requiresAuth = true,
  }) async {
    final target = resolveRequestTarget(endpoint);
    if (target.blockedResponse case final response?) throw ApiOfflineException(response);
    final headers = await _getHeaders(endpoint, requiresAuth: requiresAuth);
    final request = http.MultipartRequest('POST', target.uri!);
    request.headers.addAll(headers);
    if (fields != null) request.fields.addAll(fields);
    if (files != null) request.files.addAll(files);
    final streamed = await client.send(request).timeout(uploadTimeout);
    return http.Response.fromStream(streamed).timeout(uploadTimeout);
  }

  /// Task 6 — form-urlencoded POST (vd. Vault ghi tài liệu — backend nhận qua
  /// `Form(...)`, không phải JSON) qua cùng resolver/offline-guard/token/
  /// `X-Workspace-Id`. Bỏ `Content-Type: application/json` mặc định để
  /// `http.Request.bodyFields` tự set `application/x-www-form-urlencoded`
  /// (giữ Content-Type JSON sẽ làm `bodyFields` ném `StateError`).
  static Future<http.Response> sendForm(
    String endpoint,
    Map<String, String> fields, {
    bool requiresAuth = true,
  }) async {
    final target = resolveRequestTarget(endpoint);
    if (target.blockedResponse case final response?) throw ApiOfflineException(response);
    final headers = await _getHeaders(endpoint, requiresAuth: requiresAuth);
    headers.remove('Content-Type');
    return client.post(target.uri!, headers: headers, body: fields).timeout(defaultTimeout);
  }
}
