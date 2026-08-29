import 'dart:convert';
import 'package:http/http.dart' as http;
import '../services/secure_storage_service.dart';

class ApiClient {
  static const String _configuredBaseUrl = String.fromEnvironment('API_BASE_URL');
  static String? _customBaseUrl;

  static const String _configuredPlatformBaseUrl = String.fromEnvironment('PLATFORM_BASE_URL');
  static String? _customPlatformBaseUrl;

  static const String _configuredAgentOsUrl = String.fromEnvironment('AGENTOS_BASE_URL');
  static String? _customAgentOsUrl;

  static const String _configuredDesktopWorkerUrl = String.fromEnvironment('DESKTOP_WORKER_BASE_URL');
  static String? _customDesktopWorkerUrl;

  static void setBaseUrl(String url) {
    _customBaseUrl = url;
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

  /// Base API URL for Local Company Microservices. Defaults to `http://localhost:4000`.
  static String get baseUrl {
    if (_customBaseUrl != null && _customBaseUrl!.isNotEmpty) return _customBaseUrl!;
    if (_configuredBaseUrl.isNotEmpty) return _configuredBaseUrl;
    return 'http://localhost:4000';
  }

  /// Base API URL for COSA Central Control Plane (Platform Identity, Companies, Licenses).
  /// Defaults to `PLATFORM_BASE_URL` env, or falls back to `http://localhost:4001`.
  static String get platformBaseUrl {
    if (_customPlatformBaseUrl != null && _customPlatformBaseUrl!.isNotEmpty) return _customPlatformBaseUrl!;
    if (_configuredPlatformBaseUrl.isNotEmpty) return _configuredPlatformBaseUrl;
    return 'http://localhost:4001';
  }

  /// Base API URL for AgentOS (AI Multi-Agent Plane). Defaults to `http://localhost:8001`
  /// (service `cosa-api`, `apps/cosa/api/routes.py` — không phải `brain-api` :8000, service
  /// đó đang hỏng và bị đóng băng theo ADR-012).
  static String get agentOsBaseUrl {
    if (_customAgentOsUrl != null && _customAgentOsUrl!.isNotEmpty) return _customAgentOsUrl!;
    if (_configuredAgentOsUrl.isNotEmpty) return _configuredAgentOsUrl;
    return 'http://localhost:8001';
  }

  /// Base API URL for Desktop Worker (Loopback Execution Plane). Defaults to `http://127.0.0.1:8765`.
  static String get desktopWorkerBaseUrl {
    if (_customDesktopWorkerUrl != null && _customDesktopWorkerUrl!.isNotEmpty) return _customDesktopWorkerUrl!;
    if (_configuredDesktopWorkerUrl.isNotEmpty) return _configuredDesktopWorkerUrl;
    return 'http://127.0.0.1:8765';
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

  /// Resolves the absolute URI based on gateway target (ControlPlane :4001, AgentOS :8001, DesktopWorker :8765, or Company Encore :4000).
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
    final base = Uri.parse(baseUrl);
    final normalizedPath = normalized.startsWith('/') ? normalized : '/$normalized';
    return Uri.parse('${base.origin}$normalizedPath');
  }

  /// Overridable in tests (e.g. `ApiClient.client = MockClient(...)`) so
  /// services calling the static get/post/... methods below don't need
  /// their own http.Client injection point to be testable.
  static http.Client client = http.Client();

  /// M1 §1 — trust boundary: chọn token theo TARGET đã resolve, không theo text
  /// của path. `/platform/*` (control-plane) và `/agent/*` (AgentOS) dùng
  /// `platform_access_token`; local business service + local worker dùng
  /// `local_session_token`. Fallback `auth_token` cho phiên đã đăng nhập trước
  /// khi tách key (không ép logout).
  static Future<String?> _tokenForEndpoint(String endpoint) async {
    final normalized = normalizeEndpoint(endpoint.trim());
    final isPlatformTarget = normalized.startsWith('/platform') ||
        normalized == '/agent' ||
        normalized.startsWith('/agent/') ||
        normalized.startsWith('/agent?');

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

  static Future<http.Response> get(String endpoint, {bool requiresAuth = true}) async {
    final headers = await _getHeaders(endpoint, requiresAuth: requiresAuth);
    final url = resolveUri(endpoint);
    return client.get(url, headers: headers);
  }

  static Future<http.Response> post(String endpoint, {Map<String, dynamic>? body, bool requiresAuth = true}) async {
    final headers = await _getHeaders(endpoint, requiresAuth: requiresAuth);
    final url = resolveUri(endpoint);
    return client.post(url, headers: headers, body: body != null ? jsonEncode(body) : null);
  }

  static Future<http.Response> put(String endpoint, {Map<String, dynamic>? body, bool requiresAuth = true}) async {
    final headers = await _getHeaders(endpoint, requiresAuth: requiresAuth);
    final url = resolveUri(endpoint);
    return client.put(url, headers: headers, body: body != null ? jsonEncode(body) : null);
  }

  static Future<http.Response> patch(String endpoint, {Map<String, dynamic>? body, bool requiresAuth = true}) async {
    final headers = await _getHeaders(endpoint, requiresAuth: requiresAuth);
    final url = resolveUri(endpoint);
    return client.patch(url, headers: headers, body: body != null ? jsonEncode(body) : null);
  }

  static Future<http.Response> delete(String endpoint, {bool requiresAuth = true}) async {
    final headers = await _getHeaders(endpoint, requiresAuth: requiresAuth);
    final url = resolveUri(endpoint);
    return client.delete(url, headers: headers);
  }
}
