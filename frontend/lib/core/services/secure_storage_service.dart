import 'package:flutter/foundation.dart' show FlutterError;
import 'package:flutter/services.dart' show MissingPluginException, PlatformException;
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:shared_preferences/shared_preferences.dart';

/// Wrapper quanh flutter_secure_storage cho các giá trị nhạy cảm
/// (auth_token/workspace_id/brain_id/role) — trước đây các giá trị này nằm
/// plaintext trong SharedPreferences (Keychain/Keystore mới đúng chỗ chứa bí
/// mật, xem docs/implementation/production-runtime-closure.md Phase 2 item 4).
class SecureStorageService {
  static const _storage = FlutterSecureStorage();

  /// Các key nhạy cảm cần migrate 1 lần từ SharedPreferences sang secure
  /// storage — user hiện tại không bị logout đột ngột.
  static const _migratedKeys = ['auth_token', 'workspace_id', 'brain_id', 'role'];

  /// `flutter_secure_storage` chạy qua platform MethodChannel, vốn không tồn
  /// tại trong `flutter test` (widget test binding không đăng ký plugin
  /// native, và nhiều test file dùng `test()` trần từ package:flutter_test
  /// nên `ServicesBinding.instance` cũng chưa init khi gọi thẳng). Fallback
  /// sang SharedPreferences khi gặp đúng 2 lớp lỗi này để test hiện có (dùng
  /// `SharedPreferences.setMockInitialValues`) không phải sửa hàng loạt —
  /// production luôn có binding + platform channel thật (khởi tạo qua
  /// `runApp()` trong main.dart) nên nhánh này không bao giờ chạy ở runtime thật.
  static bool _isTestEnvironmentGap(Object e) =>
      e is MissingPluginException ||
      (e is PlatformException && e.code == 'MissingPluginException') ||
      (e is FlutterError && e.toString().contains('Binding has not yet been initialized'));

  static Future<void> write(String key, String value) => _writeSecureOrFallback(key, value);

  /// Trả về true nếu ghi được vào secure storage THẬT (Keychain/Keystore),
  /// false nếu phải fallback sang SharedPreferences (chỉ xảy ra trong
  /// `flutter test`). `migrateFromSharedPreferences()` dùng giá trị trả về
  /// này để quyết định có an toàn xoá key cũ khỏi SharedPreferences hay
  /// không — false nghĩa là giá trị vẫn đang nằm trong chính
  /// SharedPreferences (đường fallback), xoá ngay sau khi ghi sẽ mất dữ liệu.
  static Future<bool> _writeSecureOrFallback(String key, String value) async {
    try {
      await _storage.write(key: key, value: value);
      return true;
    } catch (e) {
      if (!_isTestEnvironmentGap(e)) rethrow;
      final prefs = await SharedPreferences.getInstance();
      await prefs.setString(key, value);
      return false;
    }
  }

  static Future<String?> read(String key) async {
    try {
      return await _storage.read(key: key);
    } catch (e) {
      if (!_isTestEnvironmentGap(e)) rethrow;
      final prefs = await SharedPreferences.getInstance();
      return prefs.getString(key);
    }
  }

  static Future<void> delete(String key) async {
    try {
      await _storage.delete(key: key);
    } catch (e) {
      if (!_isTestEnvironmentGap(e)) rethrow;
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
