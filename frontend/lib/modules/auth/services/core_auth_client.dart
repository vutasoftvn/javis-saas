import 'dart:convert';
import 'dart:math';

import 'package:crypto/crypto.dart';
import 'package:http/http.dart' as http;

/// Cấu hình backend/core (danh tính, mật khẩu, OIDC). Đặt bằng
/// `--dart-define=CORE_BASE_URL=https://...`; mặc định là core chạy local ở cổng 4000.
class CoreConfig {
  static const String _configuredBaseUrl = String.fromEnvironment(
    'CORE_BASE_URL',
    defaultValue: 'http://127.0.0.1:4000',
  );
  static String? _overrideBaseUrl;

  static String get baseUrl => _overrideBaseUrl ?? _configuredBaseUrl;

  /// Cho integration test trỏ core về fixture server; truyền null để trả về cấu hình mặc định.
  static void overrideBaseUrl(String? url) => _overrideBaseUrl = url;

  /// client_id (public, Authorization Code + PKCE) đã đăng ký ở core cho COSA.
  static const String clientId = 'vn.mivacorp.cosa';

  /// Redirect URI đã whitelist cho client; core chỉ trả `redirectUrl` trong JSON (không có
  /// điều hướng trình duyệt) nên app đọc `code` trực tiếp từ đó.
  static const String redirectUri = String.fromEnvironment(
    'CORE_REDIRECT_URI',
    defaultValue: 'http://localhost:3000/auth/callback',
  );

  static const String scope = 'openid profile email offline_access';
}

class CoreAuthException implements Exception {
  CoreAuthException(this.statusCode, this.message);

  final int statusCode;
  final String message;

  @override
  String toString() => 'CoreAuthException($statusCode): $message';
}

/// Phiên đăng nhập COSA: access token OIDC (opaque) của core dùng làm Bearer cho mọi API COSA.
class CoreSession {
  const CoreSession({
    required this.accessToken,
    required this.refreshToken,
    required this.expiresIn,
    this.user = const <String, dynamic>{},
  });

  final String accessToken;
  final String? refreshToken;
  final int expiresIn;
  final Map<String, dynamic> user;
}

/// Đăng nhập/đăng ký trực tiếp với backend/core rồi đổi lấy access token OIDC của
/// client `vn.mivacorp.cosa` (Authorization Code + PKCE). COSA không còn giữ mật khẩu.
///
/// Luồng first-party của core: `/auth/login` cấp phiên (JWT) -> `/oauth/authorize` bằng phiên đó
/// trả `redirectUrl` chứa `code` -> `/oauth/token` đổi `code` + `code_verifier` lấy access token.
class CoreAuthClient {
  CoreAuthClient({http.Client? client, String? baseUrl})
      : _client = client ?? http.Client(),
        _baseUrl = (baseUrl ?? CoreConfig.baseUrl).replaceAll(RegExp(r'/+$'), '');

  final http.Client _client;
  final String _baseUrl;
  final Random _random = Random.secure();

  static const Duration _timeout = Duration(seconds: 15);

  Map<String, String> get _jsonHeaders => {
        'Content-Type': 'application/json',
        'X-Client-ID': CoreConfig.clientId,
      };

  Uri _uri(String path, [Map<String, String>? query]) =>
      Uri.parse('$_baseUrl$path').replace(queryParameters: query);

  Future<CoreSession> login(String identifier, String password, {String? deviceId}) async {
    final response = await _client
        .post(
          _uri('/auth/login'),
          headers: _jsonHeaders,
          body: jsonEncode({
            'emailOrPhone': identifier,
            'password': password,
            'clientId': CoreConfig.clientId,
            'deviceId': ?deviceId,
          }),
        )
        .timeout(_timeout);
    return _exchangeSession(_decode(response));
  }

  /// Bước 1 đăng ký: core gửi OTP tới email.
  Future<void> requestSignupOtp({required String email, required String displayName}) async {
    final response = await _client
        .post(
          _uri('/auth/signup'),
          headers: _jsonHeaders,
          body: jsonEncode({
            'email': email,
            'displayName': displayName,
            'clientId': CoreConfig.clientId,
          }),
        )
        .timeout(_timeout);
    _decode(response);
  }

  /// Bước 2 đăng ký: xác nhận OTP, đặt mật khẩu và nhận phiên.
  Future<CoreSession> completeSignup({
    required String email,
    required String password,
    required String otp,
    required String displayName,
    String? preferredLanguage,
  }) async {
    final response = await _client
        .post(
          _uri('/auth/signup/complete'),
          headers: _jsonHeaders,
          body: jsonEncode({
            'emailOrPhone': email,
            'password': password,
            'otp': otp,
            'displayName': displayName,
            'clientId': CoreConfig.clientId,
            'preferredLanguage': ?preferredLanguage,
          }),
        )
        .timeout(_timeout);
    return _exchangeSession(_decode(response));
  }

  Future<CoreSession> refresh(String refreshToken) async {
    final response = await _client
        .post(
          _uri('/oauth/token'),
          headers: {'Content-Type': 'application/json'},
          body: jsonEncode({
            'grant_type': 'refresh_token',
            'refresh_token': refreshToken,
            'client_id': CoreConfig.clientId,
          }),
        )
        .timeout(_timeout);
    return _tokenResponseToSession(_decode(response), const <String, dynamic>{});
  }

  Future<CoreSession> _exchangeSession(Map<String, dynamic> sessionBody) async {
    final sessionJwt = sessionBody['accessToken'] as String?;
    if (sessionJwt == null || sessionJwt.isEmpty) {
      throw CoreAuthException(502, 'Phản hồi đăng nhập không có phiên');
    }
    final user = (sessionBody['user'] as Map?)?.cast<String, dynamic>() ?? const <String, dynamic>{};

    final verifier = _randomUrlSafe(48);
    final challenge = base64Url.encode(sha256.convert(utf8.encode(verifier)).bytes).replaceAll('=', '');
    final state = _randomUrlSafe(16);

    final authorize = await _client.get(
      _uri('/oauth/authorize', {
        'client_id': CoreConfig.clientId,
        'redirect_uri': CoreConfig.redirectUri,
        'scope': CoreConfig.scope,
        'state': state,
        'code_challenge': challenge,
        'code_challenge_method': 'S256',
      }),
      headers: {'Authorization': 'Bearer $sessionJwt'},
    ).timeout(_timeout);

    final redirectUrl = _decode(authorize)['redirectUrl'] as String?;
    final redirect = redirectUrl == null ? null : Uri.tryParse(redirectUrl);
    final code = redirect?.queryParameters['code'];
    if (code == null || code.isEmpty || redirect?.queryParameters['state'] != state) {
      throw CoreAuthException(502, 'Phản hồi authorize không hợp lệ');
    }

    final token = await _client
        .post(
          _uri('/oauth/token'),
          headers: {'Content-Type': 'application/json'},
          body: jsonEncode({
            'grant_type': 'authorization_code',
            'code': code,
            'client_id': CoreConfig.clientId,
            'redirect_uri': CoreConfig.redirectUri,
            'code_verifier': verifier,
          }),
        )
        .timeout(_timeout);
    return _tokenResponseToSession(_decode(token), user);
  }

  CoreSession _tokenResponseToSession(Map<String, dynamic> body, Map<String, dynamic> user) {
    final accessToken = body['access_token'] as String?;
    if (accessToken == null || accessToken.isEmpty) {
      throw CoreAuthException(502, 'Phản hồi token không có access_token');
    }
    return CoreSession(
      accessToken: accessToken,
      refreshToken: body['refresh_token'] as String?,
      expiresIn: (body['expires_in'] as num?)?.toInt() ?? 0,
      user: user,
    );
  }

  Map<String, dynamic> _decode(http.Response response) {
    if (response.statusCode < 200 || response.statusCode >= 300) {
      var message = 'HTTP ${response.statusCode}';
      try {
        final body = jsonDecode(response.body);
        if (body is Map && body['message'] is String) message = body['message'] as String;
      } catch (_) {}
      throw CoreAuthException(response.statusCode, message);
    }
    final body = jsonDecode(response.body);
    return body is Map<String, dynamic> ? body : <String, dynamic>{};
  }

  String _randomUrlSafe(int bytes) {
    final data = List<int>.generate(bytes, (_) => _random.nextInt(256));
    return base64Url.encode(data).replaceAll('=', '');
  }
}
