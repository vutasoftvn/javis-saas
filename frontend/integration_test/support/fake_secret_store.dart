// Task 11 — bản sao tối giản của `test/core/services/fakes/fake_secret_store.dart`
// dùng riêng cho `integration_test/` (thư mục test riêng biệt, không phụ
// thuộc `test/`) — in-memory, KHÔNG chạm Keychain/Keystore thật, KHÔNG rơi
// vào bất kỳ credential/máy thật nào của developer.
library;

import 'package:frontend/core/services/secret_store.dart';

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
}
