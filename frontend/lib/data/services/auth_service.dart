import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:flutter/foundation.dart';
import '../../core/network/api_client.dart';
import 'package:shared_preferences/shared_preferences.dart';

class AuthResult {
  final bool success;
  final String? errorMessage;
  final String? token;

  const AuthResult({
    required this.success,
    this.errorMessage,
    this.token,
  });
}

class AuthService {
  static String? _cachedToken;

  static bool get isAuthenticated => _cachedToken != null && _cachedToken!.isNotEmpty;

  static Future<void> init() async {
    final prefs = await SharedPreferences.getInstance();
    _cachedToken = prefs.getString('auth_token');
  }

  static void setCachedToken(String? token) {
    _cachedToken = token;
  }

  Future<AuthResult> login(String username, String password) async {
    try {
      final url = Uri.parse('${ApiClient.baseUrl}/auth/sessions');
      final response = await http.post(
        url,
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: {
          'username': username,
          'password': password,
        },
      );

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        final token = data['access_token'] as String?;
        if (token != null) {
          final prefs = await SharedPreferences.getInstance();
          await prefs.setString('auth_token', token);
          _cachedToken = token;
          return AuthResult(success: true, token: token);
        }
        return const AuthResult(success: false, errorMessage: 'Phản hồi không hợp lệ từ máy chủ');
      } else if (response.statusCode == 401) {
        return const AuthResult(success: false, errorMessage: 'Số điện thoại/Email hoặc mật khẩu không chính xác');
      } else if (response.statusCode == 422) {
        return const AuthResult(success: false, errorMessage: 'Dữ liệu đăng nhập không hợp lệ');
      } else {
        return AuthResult(
          success: false,
          errorMessage: 'Đăng nhập không thành công (mã lỗi ${response.statusCode})',
        );
      }
    } catch (e) {
      debugPrint('Login error: $e');
      return AuthResult(
        success: false,
        errorMessage: 'Lỗi kết nối đến máy chủ. Vui lòng kiểm tra lại mạng.',
      );
    }
  }

  Future<AuthResult> register(String phone, String password, String displayName) async {
    try {
      final response = await ApiClient.post(
        '/auth/register',
        requiresAuth: false,
        body: {
          'phone': phone,
          'password': password,
          'display_name': displayName,
        },
      );

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        final token = data['access_token'] as String?;
        if (token != null) {
          final prefs = await SharedPreferences.getInstance();
          await prefs.setString('auth_token', token);
          _cachedToken = token;
          return AuthResult(success: true, token: token);
        }
        return const AuthResult(success: false, errorMessage: 'Phản hồi không hợp lệ từ máy chủ');
      } else if (response.statusCode == 409) {
        return const AuthResult(success: false, errorMessage: 'Số điện thoại này đã được đăng ký');
      } else if (response.statusCode == 422) {
        try {
          final data = jsonDecode(response.body);
          final detail = data['detail'];
          if (detail is List && detail.isNotEmpty) {
            final msg = detail[0]['msg'] ?? 'Dữ liệu không hợp lệ';
            return AuthResult(success: false, errorMessage: msg.toString());
          }
        } catch (_) {}
        return const AuthResult(
          success: false,
          errorMessage: 'Số điện thoại (9-15 số) hoặc mật khẩu (>= 6 ký tự) không hợp lệ',
        );
      } else {
        return AuthResult(
          success: false,
          errorMessage: 'Đăng ký không thành công (mã lỗi ${response.statusCode})',
        );
      }
    } catch (e) {
      debugPrint('Register error: $e');
      return AuthResult(
        success: false,
        errorMessage: 'Lỗi kết nối đến máy chủ. Vui lòng kiểm tra lại mạng.',
      );
    }
  }

  Future<Map<String, dynamic>?> getMe() async {
    try {
      final response = await ApiClient.get('/auth/me');
      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        
        // Caching workspace and brain IDs for subsequent calls
        final prefs = await SharedPreferences.getInstance();
        if (data['workspace_id'] != null) {
          await prefs.setString('workspace_id', data['workspace_id']);
        }
        if (data['brain_id'] != null) {
          await prefs.setString('brain_id', data['brain_id']);
        }
        if (data['role'] != null) {
          // Strategy Canvas 1-1-3: Foundation tab cần biết role để ẩn/hiện nút
          // "Phê duyệt" (chỉ admin/founder được approve, xem strategy_canvas_service.py).
          await prefs.setString('role', data['role']);
        }
        
        return data;
      }
      return null;
    } catch (e) {
      debugPrint('GetMe error: $e');
      return null;
    }
  }

  Future<void> logout() async {
    _cachedToken = null;
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove('auth_token');
    await prefs.remove('workspace_id');
    await prefs.remove('brain_id');
    await prefs.remove('role');
  }

  Future<String?> getCachedRole() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString('role');
  }
}
