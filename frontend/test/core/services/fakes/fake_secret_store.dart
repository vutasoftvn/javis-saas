import 'package:flutter/services.dart' show PlatformException;
import 'package:frontend/core/services/secret_store.dart';

/// Secret store giả in-memory — chứng minh widget test có thể tiêm thẳng
/// một [SecretStore] qua `SecureStorageService.configureForTest` mà không
/// cần mock MethodChannel của flutter_secure_storage, cũng không cần
/// heuristic phát hiện widget test binding (`_isWidgetTest` cũ đã bị xoá).
class FakeSecretStore implements SecretStore {
  final Map<String, String> _values = {};

  @override
  Future<void> write(String key, String value) async {
    _values[key] = value;
  }

  @override
  Future<String?> read(String key) async => _values[key];

  @override
  Future<void> delete(String key) async {
    _values.remove(key);
  }

  bool containsKey(String key) => _values.containsKey(key);
}

/// Secret store giả luôn ném `PlatformException` — mô phỏng Keychain/Keystore
/// báo lỗi (bị khoá, thiết bị chưa unlock...) để test khẳng định lỗi này
/// PHẢI propagate nguyên vẹn cho secret key, không có đường lùi sang
/// SharedPreferences.
class ThrowingSecretStore implements SecretStore {
  const ThrowingSecretStore();

  static PlatformException get _error => PlatformException(
    code: 'keychain_error',
    message: 'Keychain is unavailable',
  );

  @override
  Future<void> write(String key, String value) async => throw _error;

  @override
  Future<String?> read(String key) async => throw _error;

  @override
  Future<void> delete(String key) async => throw _error;
}
