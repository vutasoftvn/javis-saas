import 'dart:convert';

import 'package:http/http.dart' as http;

import '../../../core/network/platform_token_provider.dart';
import 'core_auth_client.dart';

/// Kết quả bước 1 đổi số điện thoại: Core đã gửi OTP tới số mới.
class CorePhoneChallenge {
  const CorePhoneChallenge({required this.phone, required this.message});

  final String phone;
  final String message;
}

/// API profile của backend/core (spec 2026-09-25 §8). Phone và tên hiển thị
/// thuộc Core nên app ghi thẳng vào Core bằng access token OIDC của COSA;
/// COSA chỉ giữ bản chiếu read-only, không bao giờ nhận các trường này.
class CoreProfileClient {
  CoreProfileClient({
    http.Client? client,
    String? baseUrl,
    Future<String?> Function()? accessToken,
  })  : _client = client ?? http.Client(),
        _baseUrl = (baseUrl ?? CoreConfig.baseUrl).replaceAll(RegExp(r'/+$'), ''),
        _accessToken = accessToken ?? PlatformTokenProvider.currentToken;

  final http.Client _client;
  final String _baseUrl;
  final Future<String?> Function() _accessToken;

  static const Duration _timeout = Duration(seconds: 15);

  /// `PATCH /profile/display-name` — trả về tên hiển thị Core đã lưu.
  Future<String> updateDisplayName(String displayName) async {
    final body = await _send('PATCH', '/profile/display-name', {'displayName': displayName});
    final saved = body['displayName'];
    if (body['success'] != true || saved is! String || saved.isEmpty) {
      throw CoreAuthException(502, 'Phản hồi đổi tên hiển thị không hợp lệ');
    }
    return saved;
  }

  /// `POST /profile/phone/change` — Core gửi OTP tới số mới, số chưa đổi.
  Future<CorePhoneChallenge> requestPhoneChange(String newPhone) async {
    final body = await _send('POST', '/profile/phone/change', {'newPhone': newPhone});
    final phone = body['phone'];
    if (phone is! String || phone.isEmpty) {
      throw CoreAuthException(502, 'Phản hồi đổi số điện thoại không hợp lệ');
    }
    return CorePhoneChallenge(phone: phone, message: (body['message'] ?? '').toString());
  }

  /// `POST /profile/phone/verify` — xác nhận OTP; chỉ khi đó số mới có hiệu lực.
  Future<String> verifyPhoneChange({required String phone, required String otp}) async {
    final body = await _send('POST', '/profile/phone/verify', {'phone': phone, 'otp': otp});
    final profile = body['profile'];
    final saved = profile is Map ? profile['phone'] : null;
    if (saved is! String || saved.isEmpty) {
      throw CoreAuthException(502, 'Phản hồi xác nhận số điện thoại không hợp lệ');
    }
    return saved;
  }

  Future<Map<String, dynamic>> _send(String method, String path, Map<String, dynamic> payload) async {
    final token = await _accessToken();
    if (token == null || token.isEmpty) {
      throw CoreAuthException(401, 'Phiên đăng nhập đã hết hạn');
    }
    final request = http.Request(method, Uri.parse('$_baseUrl$path'))
      ..headers.addAll({
        'Content-Type': 'application/json',
        'Authorization': 'Bearer $token',
        'X-Client-ID': CoreConfig.clientId,
      })
      ..body = jsonEncode(payload);
    final response = await http.Response.fromStream(await _client.send(request).timeout(_timeout));
    if (response.statusCode < 200 || response.statusCode >= 300) {
      var message = 'HTTP ${response.statusCode}';
      try {
        final decoded = jsonDecode(response.body);
        if (decoded is Map && decoded['message'] is String) message = decoded['message'] as String;
      } catch (_) {}
      throw CoreAuthException(response.statusCode, message);
    }
    final decoded = jsonDecode(response.body);
    return decoded is Map<String, dynamic> ? decoded : <String, dynamic>{};
  }
}
