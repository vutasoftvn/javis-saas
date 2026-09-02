import 'package:flutter/foundation.dart' show visibleForTesting;
import 'package:shared_preferences/shared_preferences.dart';

import 'secret_store.dart';

/// Wrapper quanh secret store cho các giá trị nhạy cảm
/// (local_session_token/platform_access_token/auth_token) — trước đây các
/// giá trị này nằm plaintext trong SharedPreferences (Keychain/Keystore mới
/// đúng chỗ chứa bí mật, xem docs/implementation/production-runtime-closure.md
/// Phase 2). M3 §7: legacy brain scope đã bị bỏ hoàn toàn — Workspace là
/// scope duy nhất.
///
/// Fail-closed theo threat model: nếu native secure storage báo lỗi
/// (Keychain khoá, chưa unlock thiết bị, plugin thiếu implementation trên
/// nền tảng hiện tại...) thì thao tác trên 1 trong 3 secret key phải throw
/// thẳng lên caller — KHÔNG có nhánh nào âm thầm ghi/đọc/xoá token qua
/// SharedPreferences plaintext. Trước đây có heuristic `_isWidgetTest` định
/// tuyến thẳng sang SharedPreferences khi chạy dưới `flutter test`, và coi
/// `PlatformException`/`MissingPluginException` là "recoverable" — cả 2 đều
/// là lỗ hổng bảo mật thật (không chỉ là vấn đề test), nay đã bỏ hẳn. Widget
/// test tiêm test double qua [configureForTest] thay vì dựa vào heuristic.
class SecureStorageService {
  static SecretStore _secretStore = const FlutterSecureSecretStore();
  static const KeyClassifier _classifier = DefaultKeyClassifier();

  /// Các key nhạy cảm cần migrate 1 lần từ SharedPreferences sang secure
  /// storage — user hiện tại không bị logout đột ngột. CHỈ chứa secret key:
  /// workspace_id/role không cần migrate vì chỗ chứa đích của chúng vẫn là
  /// SharedPreferences (xem rationale ở dưới) — không có nơi nào để "chuyển
  /// đến", nên không có gì phải di dời.
  static const _migratedKeys = [
    'auth_token', // legacy — token chung, đang được tách (M1 §1)
    'local_session_token', // local business service (ký JWT_SECRET)
    'platform_access_token', // control-plane + AgentOS platform path
  ];

  // M1 §1 — key theo trust boundary.
  static const localSessionTokenKey = 'local_session_token';
  static const platformAccessTokenKey = 'platform_access_token';

  /// Threat model cho key không-phải-token (workspace_id, role): đây KHÔNG
  /// phải bearer credential — tự thân chúng không đủ để giả mạo một request
  /// (không như token, chỉ cần token là gọi được API), nên không bắt buộc
  /// phải nằm trong Keychain/Keystore như 3 secret key ở trên; SharedPreferences
  /// (cache store hiện có) là đủ. Nhưng chúng vẫn tiết lộ ngữ cảnh tenant/
  /// quyền hạn (workspace nào, role gì) — hữu ích cho social engineering
  /// hoặc lộ diện cấu trúc tổ chức nếu thiết bị bị truy cập — nên việc định
  /// tuyến qua `_classifier`/`write`/`read`/`delete` ở đây là có chủ đích
  /// (khác về mặt xử lý với secret key), không phải coi chúng ngang hàng với
  /// cache ứng dụng tuỳ ý một cách vô thức. Cố tình KHÔNG đặt prefix/namespace
  /// riêng trong SharedPreferences cho 2 key này: rất nhiều test hiện có
  /// seed thẳng `SharedPreferences.setMockInitialValues({'workspace_id': ...})`
  /// dưới tên key gốc — đổi namespace sẽ phá vỡ hàng loạt test không liên
  /// quan tới bảo mật token (phạm vi ngoài task này) mà không tăng thêm an
  /// toàn thực chất nào (đã chấp nhận plaintext ở threat model trên).

  /// Tiêm secret store giả (in-memory) cho widget test — không cần mock
  /// MethodChannel của flutter_secure_storage, không cần heuristic phát hiện
  /// widget test binding. CHỈ dùng trong test.
  @visibleForTesting
  static void configureForTest(SecretStore store) {
    _secretStore = store;
  }

  /// Khôi phục secret store thật — gọi trong `tearDown` để test sau không bị
  /// ảnh hưởng bởi fake của test trước.
  @visibleForTesting
  static void resetForTest() {
    _secretStore = const FlutterSecureSecretStore();
  }

  static Future<void> write(String key, String value) async {
    if (_classifier.isSecret(key)) {
      // Không catch: lỗi native phải propagate nguyên vẹn, không có đường
      // lùi sang SharedPreferences cho secret key.
      await _secretStore.write(key, value);
      return;
    }
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(key, value);
  }

  static Future<String?> read(String key) async {
    if (_classifier.isSecret(key)) {
      return _secretStore.read(key);
    }
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString(key);
  }

  static Future<void> delete(String key) async {
    if (_classifier.isSecret(key)) {
      await _secretStore.delete(key);
      return;
    }
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(key);
  }

  /// Đọc giá trị plaintext cũ của 3 secret key (còn sót từ trước khi có
  /// secure storage) từ SharedPreferences CHỈ để thử ghi an toàn sang secret
  /// store thật — chỉ xoá bản plaintext cũ SAU KHI ghi an toàn thành công.
  /// Nếu ghi thất bại (v.d Keychain lỗi), `write` ở trên throw ngay, vòng
  /// lặp dừng lại và bản plaintext cũ của key đó (và các key chưa xử lý) vẫn
  /// còn nguyên — không bao giờ xoá-trước-rồi-ghi, không bao giờ để mất cả 2
  /// bản do lỗi giữa chừng. Idempotent — chạy nhiều lần an toàn vì
  /// SharedPreferences không còn key cũ sau lần migrate thành công.
  /// workspace_id/role không nằm trong `_migratedKeys` — xem rationale ở
  /// trên, chúng vẫn ở nguyên SharedPreferences nên không có gì để migrate.
  static Future<void> migrateFromSharedPreferences() async {
    final prefs = await SharedPreferences.getInstance();
    for (final key in _migratedKeys) {
      final legacyValue = prefs.getString(key);
      if (legacyValue == null) continue;
      await write(key, legacyValue);
      await prefs.remove(key);
    }
  }
}
