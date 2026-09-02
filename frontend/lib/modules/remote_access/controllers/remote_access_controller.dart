import 'package:get/get.dart';
import '../models/runtime_status.dart';

/// Task 5 — MỘT nguồn sự thật runtime duy nhất: `SessionController._commit`
/// (Task 4) là nơi DUY NHẤT quyết định `ApiClient.runtimeMode`/`nodePresence`
/// (qua `ApiClient.setRuntimeContext`/`clearRuntimeContext`). Controller này
/// KHÔNG còn tự gọi `ApiClient` — chỉ giữ [status] để UI (RuntimeAppChrome/
/// RemoteAccessBanner) đọc, nhận snapshot DUY NHẤT từ SessionController (qua
/// [applyStatus]), không tự parse JSON picker hay bất kỳ nguồn nào khác.
/// Trước đây `applyStatus`/`reset`/`onClose` đều tự gọi thẳng
/// `ApiClient.setRuntimeContext`/`clearRuntimeContext` — hai nơi cùng ghi một
/// state dễ lệch pha (vd. `onClose` xoá runtime context của SessionController
/// hiện tại chỉ vì widget con bị dispose không liên quan gì đến logout).
class RemoteAccessController extends GetxController {
  final Rxn<RuntimeStatus> status = Rxn<RuntimeStatus>();

  bool get isReadOnly => status.value?.isReadOnly ?? false;
  bool get isOffline => status.value?.isOffline ?? false;

  /// Gọi bởi `SessionController._commit` sau khi ApiClient runtime context
  /// đã được thiết lập — CHỈ cập nhật state hiển thị, không lặp lại side
  /// effect lên ApiClient (đã do SessionController làm trong cùng khối commit).
  void applyStatus(RuntimeStatus s) {
    status.value = s;
  }

  /// Gọi bởi `SessionController.logout` — chỉ xoá state hiển thị, việc xoá
  /// `ApiClient` runtime context do `SessionController.logout` tự làm trước
  /// đó (thứ tự bắt buộc: stop realtime → clear ApiClient runtime → clear
  /// memory, xem `session_controller.dart`).
  void reset() {
    status.value = null;
  }
}
