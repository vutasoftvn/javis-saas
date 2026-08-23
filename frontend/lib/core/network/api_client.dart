import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';

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

  /// Base API URL for AgentOS (AI Multi-Agent Plane). Defaults to `http://localhost:8000`.
  static String get agentOsBaseUrl {
    if (_customAgentOsUrl != null && _customAgentOsUrl!.isNotEmpty) return _customAgentOsUrl!;
    if (_configuredAgentOsUrl.isNotEmpty) return _configuredAgentOsUrl;
    return 'http://localhost:8000';
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
    if (normalized.startsWith('/api/v1')) {
      normalized = normalized.substring(7);
    }
    if (normalized.startsWith('/auth/')) {
      return '/identity/${normalized.substring(6)}';
    }
    if (normalized == '/auth' || normalized == '/auth/me') {
      return '/identity/me';
    }
    if (normalized.startsWith('/tasks')) {
      return '/operations$normalized';
    }
    if (normalized.startsWith('/strategy/')) {
      return '/operations/${normalized.substring(10)}';
    }
    if (normalized.startsWith('/sales/')) {
      return '/commercial/${normalized.substring(7)}';
    }
    if (normalized.startsWith('/marketing/')) {
      return '/commercial/marketing/${normalized.substring(11)}';
    }
    if (normalized.startsWith('/finance/')) {
      return '/finance-legal/${normalized.substring(9)}';
    }
    if (normalized.startsWith('/legal/')) {
      return '/finance-legal/${normalized.substring(7)}';
    }
    return normalized;
  }

  /// Resolves the absolute URI based on gateway target (ControlPlane, AgentOS, DesktopWorker, or Company Encore).
  static Uri resolveUri(String endpoint) {
    String path = endpoint.trim();
    if (path.startsWith('/api/v1')) {
      path = path.substring(7);
    }
    if (path.startsWith('/platform/') || path == '/platform') {
      final base = Uri.parse(platformBaseUrl);
      final normalizedPath = path.startsWith('/') ? path : '/$path';
      return Uri.parse('${base.origin}$normalizedPath');
    }
    if (path.startsWith('/agent/') || path == '/agent') {
      final base = Uri.parse(agentOsBaseUrl);
      final normalizedPath = path.startsWith('/') ? path : '/$path';
      return Uri.parse('${base.origin}$normalizedPath');
    }
    if (path.startsWith('/local-worker/')) {
      final base = Uri.parse(desktopWorkerBaseUrl);
      final subPath = path.substring(13); // strip '/local-worker'
      final normalizedPath = subPath.startsWith('/') ? subPath : '/$subPath';
      return Uri.parse('${base.origin}$normalizedPath');
    }
    final normalized = normalizeEndpoint(path);
    final base = Uri.parse(baseUrl);
    final normalizedPath = normalized.startsWith('/') ? normalized : '/$normalized';
    return Uri.parse('${base.origin}$normalizedPath');
  }

  /// Overridable in tests (e.g. `ApiClient.client = MockClient(...)`) so
  /// services calling the static get/post/... methods below don't need
  /// their own http.Client injection point to be testable.
  static http.Client client = http.Client();

  static Future<Map<String, String>> _getHeaders({bool requiresAuth = true}) async {
    final headers = {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
    };

    if (requiresAuth) {
      final prefs = await SharedPreferences.getInstance();
      final token = prefs.getString('auth_token');
      if (token != null && token.isNotEmpty) {
        headers['Authorization'] = 'Bearer $token';
      }
      final workspaceId = prefs.getString('workspace_id');
      if (workspaceId != null && workspaceId.isNotEmpty) {
        headers['X-Workspace-Id'] = workspaceId;
      }
      final companyId = prefs.getString('company_id');
      if (companyId != null && companyId.isNotEmpty) {
        headers['X-Company-Id'] = companyId;
      }
    }

    return headers;
  }

  static Future<http.Response> get(String endpoint, {bool requiresAuth = true}) async {
    final headers = await _getHeaders(requiresAuth: requiresAuth);
    final url = resolveUri(endpoint);
    return client.get(url, headers: headers);
  }

  static Future<http.Response> post(String endpoint, {Map<String, dynamic>? body, bool requiresAuth = true}) async {
    final headers = await _getHeaders(requiresAuth: requiresAuth);
    final url = resolveUri(endpoint);
    return client.post(url, headers: headers, body: body != null ? jsonEncode(body) : null);
  }

  static Future<http.Response> put(String endpoint, {Map<String, dynamic>? body, bool requiresAuth = true}) async {
    final headers = await _getHeaders(requiresAuth: requiresAuth);
    final url = resolveUri(endpoint);
    return client.put(url, headers: headers, body: body != null ? jsonEncode(body) : null);
  }

  static Future<http.Response> patch(String endpoint, {Map<String, dynamic>? body, bool requiresAuth = true}) async {
    final headers = await _getHeaders(requiresAuth: requiresAuth);
    final url = resolveUri(endpoint);
    return client.patch(url, headers: headers, body: body != null ? jsonEncode(body) : null);
  }

  static Future<http.Response> delete(String endpoint, {bool requiresAuth = true}) async {
    final headers = await _getHeaders(requiresAuth: requiresAuth);
    final url = resolveUri(endpoint);
    return client.delete(url, headers: headers);
  }
}
