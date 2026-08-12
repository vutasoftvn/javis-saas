import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';

class ApiClient {
  static const String _configuredBaseUrl = String.fromEnvironment('API_BASE_URL');

  /// The Android emulator's loopback interface is isolated from the host
  /// machine's, so `localhost` there points at the emulator itself, not the
  /// dev machine running the backend; `10.0.2.2` is the emulator's alias for
  /// the host loopback. iOS Simulator has no such split, so `localhost` works.
  static String get baseUrl {
    if (_configuredBaseUrl.isNotEmpty) return _configuredBaseUrl;
    if (!kIsWeb && defaultTargetPlatform == TargetPlatform.android) {
      return 'http://10.0.2.2:8000/api/v1';
    }
    return 'http://localhost:8000/api/v1';
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
    }

    return headers;
  }

  static Future<http.Response> get(String endpoint, {bool requiresAuth = true}) async {
    final headers = await _getHeaders(requiresAuth: requiresAuth);
    final url = Uri.parse('$baseUrl$endpoint');
    return client.get(url, headers: headers);
  }

  static Future<http.Response> post(String endpoint, {Map<String, dynamic>? body, bool requiresAuth = true}) async {
    final headers = await _getHeaders(requiresAuth: requiresAuth);
    final url = Uri.parse('$baseUrl$endpoint');
    return client.post(url, headers: headers, body: body != null ? jsonEncode(body) : null);
  }

  static Future<http.Response> put(String endpoint, {Map<String, dynamic>? body, bool requiresAuth = true}) async {
    final headers = await _getHeaders(requiresAuth: requiresAuth);
    final url = Uri.parse('$baseUrl$endpoint');
    return client.put(url, headers: headers, body: body != null ? jsonEncode(body) : null);
  }

  static Future<http.Response> patch(String endpoint, {Map<String, dynamic>? body, bool requiresAuth = true}) async {
    final headers = await _getHeaders(requiresAuth: requiresAuth);
    final url = Uri.parse('$baseUrl$endpoint');
    return client.patch(url, headers: headers, body: body != null ? jsonEncode(body) : null);
  }

  static Future<http.Response> delete(String endpoint, {bool requiresAuth = true}) async {
    final headers = await _getHeaders(requiresAuth: requiresAuth);
    final url = Uri.parse('$baseUrl$endpoint');
    return client.delete(url, headers: headers);
  }
}
