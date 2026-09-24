import '../../modules/auth/services/core_auth_client.dart';
import '../services/secure_storage_service.dart';

/// Access token OIDC của backend/core dùng cho mọi API `/platform/*` (COSA control plane).
/// Token có hạn ngắn nên provider tự làm mới bằng refresh token khi sắp hết hạn; nhiều request đồng
/// thời chỉ làm mới một lần. Phiên cũ (JWT platform 7 ngày, không có hạn/refresh token) trả nguyên.
class PlatformTokenProvider {
  static const _accessKey = 'platform_access_token';
  static const _refreshKey = 'core_refresh_token';
  static const _expiresKey = 'platform_access_expires_at';
  static const Duration _refreshSkew = Duration(seconds: 60);

  static CoreAuthClient? _coreAuth;
  static DateTime Function() _now = DateTime.now;
  static Future<void>? _inflightRefresh;

  static CoreAuthClient get _core => _coreAuth ??= CoreAuthClient();

  static void configureForTest({CoreAuthClient? coreAuth, DateTime Function()? now}) {
    _coreAuth = coreAuth;
    if (now != null) _now = now;
    _inflightRefresh = null;
  }

  static void resetForTest() {
    _coreAuth = null;
    _now = DateTime.now;
    _inflightRefresh = null;
  }

  static Future<void> saveSession(CoreSession session) async {
    await SecureStorageService.write(_accessKey, session.accessToken);
    final refresh = session.refreshToken;
    if (refresh != null && refresh.isNotEmpty) {
      await SecureStorageService.write(_refreshKey, refresh);
    }
    if (session.expiresIn > 0) {
      final expiresAt = _now().add(Duration(seconds: session.expiresIn));
      await SecureStorageService.write(_expiresKey, expiresAt.millisecondsSinceEpoch.toString());
    } else {
      await SecureStorageService.delete(_expiresKey);
    }
  }

  static Future<void> clear() async {
    await SecureStorageService.delete(_accessKey);
    await SecureStorageService.delete(_refreshKey);
    await SecureStorageService.delete(_expiresKey);
  }

  /// Access token còn hiệu lực để gửi tới control plane, hoặc null nếu chưa đăng nhập.
  static Future<String?> currentToken() async {
    if (await _needsRefresh()) {
      await (_inflightRefresh ??= _refresh().whenComplete(() => _inflightRefresh = null));
    }
    final token = await SecureStorageService.read(_accessKey);
    return (token != null && token.isNotEmpty) ? token : null;
  }

  static Future<bool> _needsRefresh() async {
    final expires = await SecureStorageService.read(_expiresKey);
    final refresh = await SecureStorageService.read(_refreshKey);
    if (expires == null || refresh == null || refresh.isEmpty) return false;
    final expiresAtMs = int.tryParse(expires);
    if (expiresAtMs == null) return false;
    final deadline = DateTime.fromMillisecondsSinceEpoch(expiresAtMs).subtract(_refreshSkew);
    return !_now().isBefore(deadline);
  }

  static Future<void> _refresh() async {
    final refresh = await SecureStorageService.read(_refreshKey);
    if (refresh == null || refresh.isEmpty) return;
    try {
      await saveSession(await _core.refresh(refresh));
    } catch (_) {
      // Không nuốt thành "chưa đăng nhập": giữ token hiện có để server quyết định (401 nếu hết hạn thật).
    }
  }
}
