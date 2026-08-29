import 'package:get/get.dart';
import '../../../core/network/api_client.dart';
import '../models/runtime_status.dart';

/// M5 §5/§6 — giữ [RuntimeStatus] hiện hành và ĐỒNG BỘ nó xuống [ApiClient]
/// (`runtimeMode` + `nodePresence`) để routing + offline guard hoạt động.
///
/// Nạp lại khi: login xong, switch workspace, hoặc poll định kỳ. Việc fetch
/// thật (endpoint platform trả runtime_mode + presence) là adapter bên ngoài —
/// controller này chỉ nhận status và áp dụng.
class RemoteAccessController extends GetxController {
  final Rxn<RuntimeStatus> status = Rxn<RuntimeStatus>();

  bool get isReadOnly => status.value?.isReadOnly ?? false;
  bool get isOffline => status.value?.isOffline ?? false;

  void applyStatus(RuntimeStatus s) {
    status.value = s;
    ApiClient.setRuntimeContext(
      mode: RuntimeStatus.modeWire(s.mode),
      presence: RuntimeStatus.presenceWire(s.presence),
    );
  }

  void applyFromJson(Map<String, dynamic> json) =>
      applyStatus(RuntimeStatus.fromJson(json));

  /// Gọi khi rời workspace / logout — quay lại mặc định LOCAL_ONLY (không relay,
  /// không offline guard).
  void reset() {
    status.value = null;
    ApiClient.clearRuntimeContext();
  }

  @override
  void onClose() {
    ApiClient.clearRuntimeContext();
    super.onClose();
  }
}
