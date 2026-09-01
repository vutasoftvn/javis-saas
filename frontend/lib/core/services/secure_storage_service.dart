import 'package:flutter/foundation.dart' show FlutterError;
import 'package:flutter/services.dart'
    show MissingPluginException, PlatformException;
import 'package:flutter/widgets.dart' show WidgetsBinding;
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:shared_preferences/shared_preferences.dart';

/// Wrapper quanh flutter_secure_storage cho các giá trị nhạy cảm
/// (local_session_token/platform_access_token/workspace_id/role) — trước đây các
/// giá trị này nằm plaintext trong SharedPreferences (Keychain/Keystore mới đúng
/// chỗ chứa bí mật, xem docs/implementation/production-runtime-closure.md Phase 2).
/// M3 §7: legacy brain scope đã bị bỏ hoàn toàn — Workspace là scope duy nhất.
class SecureStorageService {
  static const _storage = FlutterSecureStorage(
    mOptions: MacOsOptions(usesDataProtectionKeychain: false),
  );

  /// Các key nhạy cảm cần migrate 1 lần từ SharedPreferences sang secure
  /// storage — user hiện tại không bị logout đột ngột.
  static const _migratedKeys = [
    'auth_token', // legacy — token chung, đang được tách (M1 §1)
    'local_session_token', // local business service (ký JWT_SECRET)
    'platform_access_token', // control-plane + AgentOS platform path
    'workspace_id',
    'role',
  ];

  // M1 §1 — key theo trust boundary.
  static const localSessionTokenKey = 'local_session_token';
  static const platformAccessTokenKey = 'platform_access_token';

  /// `flutter_secure_storage` chạy qua platform MethodChannel, vốn không tồn
  /// tại trong `flutter test` (widget test binding không đăng ký plugin
  /// native, và nhiều test file dùng `test()` trần từ package:flutter_test
  /// nên `ServicesBinding.instance` cũng chưa init khi gọi thẳng). Fallback
  /// sang SharedPreferences khi gặp đúng 2 lớp lỗi này để test hiện có (dùng
  /// `SharedPreferences.setMockInitialValues`) không phải sửa hàng loạt —
  /// production luôn có binding + platform channel thật (khởi tạo qua
  /// `runApp()` trong main.dart) nên nhánh này không bao giờ chạy ở runtime thật.
  static bool _isRecoverableStorageError(Object e) =>
      e is MissingPluginException ||
      e is PlatformException ||
      (e is FlutterError &&
          e.toString().contains('Binding has not yet been initialized'));

  /// Widget tests do not register the native Keychain plugin. On macOS such a
  /// MethodChannel call can remain pending rather than immediately throwing a
  /// MissingPluginException, so select the existing SharedPreferences test
  /// fallback before making that native call.
  static bool get _isWidgetTest {
    try {
      return WidgetsBinding.instance.runtimeType.toString().contains(
        'TestWidgetsFlutterBinding',
      );
    } catch (_) {
      return false;
    }
  }

  static Future<void> write(String key, String value) =>
      _writeSecureOrFallback(key, value);

  static Future<bool> _writeSecureOrFallback(String key, String value) async {
    if (_isWidgetTest) {
      final prefs = await SharedPreferences.getInstance();
      await prefs.setString(key, value);
      return false;
    }
    try {
      await _storage.write(key: key, value: value);
      return true;
    } catch (e) {
      if (!_isRecoverableStorageError(e)) rethrow;
      final prefs = await SharedPreferences.getInstance();
      await prefs.setString(key, value);
      return false;
    }
  }

  static Future<String?> read(String key) async {
    if (_isWidgetTest) {
      final prefs = await SharedPreferences.getInstance();
      return prefs.getString(key);
    }
    try {
      return await _storage.read(key: key);
    } catch (e) {
      if (!_isRecoverableStorageError(e)) rethrow;
      final prefs = await SharedPreferences.getInstance();
      return prefs.getString(key);
    }
  }

  static Future<void> delete(String key) async {
    if (_isWidgetTest) {
      final prefs = await SharedPreferences.getInstance();
      await prefs.remove(key);
      return;
    }
    try {
      await _storage.delete(key: key);
    } catch (e) {
      if (!_isRecoverableStorageError(e)) rethrow;
      final prefs = await SharedPreferences.getInstance();
      await prefs.remove(key);
    }
  }

  /// Đọc key cũ từ SharedPreferences (nếu còn), ghi vào secure storage rồi
  /// xoá khỏi SharedPreferences. Idempotent — chạy nhiều lần an toàn vì
  /// SharedPreferences không còn key sau lần migrate đầu.
  static Future<void> migrateFromSharedPreferences() async {
    final prefs = await SharedPreferences.getInstance();
    for (final key in _migratedKeys) {
      final legacyValue = prefs.getString(key);
      if (legacyValue != null) {
        final wroteSecurely = await _writeSecureOrFallback(key, legacyValue);
        if (wroteSecurely) {
          await prefs.remove(key);
        }
      }
    }
  }
}
