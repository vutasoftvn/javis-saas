import 'package:flutter/foundation.dart';
import 'package:get/get.dart';

import '../widgets/company_identity_modal.dart';
import 'company_identity_service.dart';

/// Điểm gắn DUY NHẤT cho yêu cầu "workspace phải có Vision/Mission/Values" —
/// gọi từ HubAuthMixin.ensureAuthenticated() nên bắt cả 2 tình huống (workspace
/// vừa tạo / workspace cũ đăng nhập lại) bằng một logic. Fail-open khi fetch
/// lỗi — không khoá app vì một request tạm thời thất bại.
class CompanyIdentityGate {
  static Future<void> checkAndPrompt(
    String workspaceId, {
    CompanyIdentityService? service,
    Future<void> Function(String workspaceId)? showModal,
  }) async {
    final svc = service ?? CompanyIdentityService();
    try {
      final identity = await svc.fetch(workspaceId);
      if (identity.isComplete) return;
    } catch (e) {
      debugPrint('[CompanyIdentityGate] fetch error, fail-open: $e');
      return;
    }

    final show = showModal ?? _showBlockingModal;
    await show(workspaceId);
  }

  static Future<void> _showBlockingModal(String workspaceId) {
    return Get.dialog<void>(
      CompanyIdentityModal(workspaceId: workspaceId),
      barrierDismissible: false,
    );
  }
}
