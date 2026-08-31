import 'package:flutter/foundation.dart';
import 'package:get/get.dart';

import '../widgets/company_identity_modal.dart';
import 'company_identity_service.dart';

/// Điểm gắn DUY NHẤT cho yêu cầu "workspace phải có Vision/Mission/Values" —
/// gọi từ HubAuthMixin.ensureAuthenticated() nên bắt cả 2 tình huống (workspace
/// vừa tạo / workspace cũ đăng nhập lại) bằng một logic. Fail-open khi fetch
/// lỗi — không khoá app vì một request tạm thời thất bại.
class CompanyIdentityGate {
  // Guard chống 2 lời gọi checkAndPrompt đè lên nhau cho cùng 1 workspace
  // (vd. ensureAuthenticated() bị trigger từ nhiều route cùng lúc) — nếu
  // không có guard này, cả hai có thể cùng thấy workspace chưa đủ dữ liệu
  // và cùng show() dialog, xếp chồng 2 modal.
  static final Set<String> _inFlight = {};

  static Future<void> checkAndPrompt(
    String workspaceId, {
    CompanyIdentityService? service,
    Future<void> Function(String workspaceId)? showModal,
  }) async {
    if (_inFlight.contains(workspaceId)) return;
    _inFlight.add(workspaceId);
    try {
      final svc = service ?? CompanyIdentityService();
      final show = showModal ?? _showBlockingModal;

      // Lặp lại sau mỗi lần show() vì modal chặn có thể bị đóng mà không
      // lưu thành công (lỗi bên trong dialog, navigation từ nơi khác...) —
      // phải re-check thật sự hoàn tất mới cho phép vào Hub.
      while (true) {
        try {
          final identity = await svc.fetch(workspaceId);
          if (identity.isComplete) return;
        } catch (e) {
          debugPrint('[CompanyIdentityGate] fetch error, fail-open: $e');
          return;
        }
        await show(workspaceId);
      }
    } finally {
      _inFlight.remove(workspaceId);
    }
  }

  static Future<void> _showBlockingModal(String workspaceId) {
    return Get.dialog<void>(
      CompanyIdentityModal(workspaceId: workspaceId),
      barrierDismissible: false,
    );
  }
}
