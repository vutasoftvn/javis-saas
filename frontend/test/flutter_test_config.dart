import 'dart:async';

import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/core/services/secure_storage_service.dart';

import 'core/services/fakes/fake_secret_store.dart';

/// Hook chạy quanh MỌI file test trong `test/` (cơ chế chuẩn của
/// package:test/flutter_test — xem https://api.flutter.dev/flutter/flutter_test/testExecutable.html).
///
/// Trước đây `SecureStorageService` có heuristic `_isWidgetTest` tự phát
/// hiện đang chạy dưới `flutter test` và âm thầm định tuyến TOÀN BỘ secret
/// key (kể cả token) sang SharedPreferences plaintext — đây chính là lỗ hổng
/// bảo mật bị Task 2 loại bỏ (native secure storage lỗi phải fail-closed,
/// không có đường lùi). Nhưng loại bỏ heuristic đó nghĩa là MỌI test gọi
/// `SecureStorageService`/`ApiAuthResolver` mà không tự tiêm test double sẽ
/// đụng thẳng MethodChannel thật của flutter_secure_storage — thứ không tồn
/// tại trong tiến trình `flutter test` (VM thuần, không phải chạy trên thiết
/// bị/simulator) — nên luôn ném `MissingPluginException`, phá hàng loạt test
/// không liên quan gì đến bảo mật token.
///
/// Vì vậy: đặt một [FakeSecretStore] MẶC ĐỊNH an toàn cho toàn bộ test suite
/// ở đây — thay heuristic ngầm bằng một seam tường minh, đúng tinh thần
/// `SecureStorageService.configureForTest`. Test nào cần khẳng định hành vi
/// fail-closed thật (v.d `secure_storage_service_test.dart`) vẫn tự do gọi
/// `configureForTest(ThrowingSecretStore())`/mock MethodChannel riêng trong
/// `setUp` của chính nó — override này chạy sau, trong từng test, nên luôn
/// thắng giá trị mặc định đặt ở đây.
Future<void> testExecutable(FutureOr<void> Function() testMain) async {
  setUp(() {
    SecureStorageService.configureForTest(FakeSecretStore());
  });
  tearDown(() {
    SecureStorageService.resetForTest();
  });
  await testMain();
}
