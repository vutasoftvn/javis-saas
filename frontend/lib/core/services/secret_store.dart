import 'package:flutter_secure_storage/flutter_secure_storage.dart';

/// Cổng ghi/đọc/xóa cho các giá trị bí mật (token). Implementation thật
/// (`FlutterSecureSecretStore`) dùng Keychain (iOS/macOS)/Keystore (Android)
/// qua `flutter_secure_storage`; widget test tiêm một fake in-memory qua
/// `SecureStorageService.configureForTest` — không cần mock MethodChannel,
/// không còn phụ thuộc heuristic "đang chạy trong widget test binding".
abstract interface class SecretStore {
  Future<void> write(String key, String value);
  Future<String?> read(String key);
  Future<void> delete(String key);
}

/// Phân loại key nào là bí mật (bearer token — đủ để giả mạo request một
/// mình nếu rò rỉ) và bắt buộc fail-closed, khác với key chỉ là ngữ cảnh
/// phiên (workspace_id, role).
abstract interface class KeyClassifier {
  bool isSecret(String key);
}

/// 3 key bearer-token duy nhất coi là bí mật theo M1 §1 — không bao giờ được
/// phép rơi xuống SharedPreferences plaintext dù native secure storage báo
/// lỗi (Keychain bị khoá, thiết bị chưa unlock, plugin thiếu implementation
/// trên nền tảng hiện tại, v.v.). Bất kỳ lỗi nào ở đây đều phải propagate
/// nguyên vẹn lên caller — không có "recoverable error" cho các key này.
const secretKeys = <String>{
  'auth_token',
  'local_session_token',
  'platform_access_token',
};

class DefaultKeyClassifier implements KeyClassifier {
  const DefaultKeyClassifier();

  @override
  bool isSecret(String key) => secretKeys.contains(key);
}

/// Adapter thật dùng flutter_secure_storage. Cố ý KHÔNG catch bất kỳ lỗi nào
/// ở đây (PlatformException, MissingPluginException, ...) — tầng gọi
/// (`SecureStorageService`) là nơi quyết định fail-closed cho secret key,
/// nhưng adapter này không được tự ý "làm mềm" lỗi native thành null/void.
class FlutterSecureSecretStore implements SecretStore {
  const FlutterSecureSecretStore();

  static const _storage = FlutterSecureStorage(
    mOptions: MacOsOptions(usesDataProtectionKeychain: false),
  );

  @override
  Future<void> write(String key, String value) =>
      _storage.write(key: key, value: value);

  @override
  Future<String?> read(String key) => _storage.read(key: key);

  @override
  Future<void> delete(String key) => _storage.delete(key: key);
}
