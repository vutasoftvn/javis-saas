import 'package:flutter/foundation.dart';
import 'package:get/get.dart';
import '../../../data/services/auth_service.dart';
import '../../../core/routing/app_routes.dart';
import '../../chat/controllers/chat_controller.dart';

class DashboardController extends GetxController {
  final AuthService _authService = AuthService();

  // Selected tab index
  final currentIndex = 0.obs;

  // Accordion mode: chỉ mở duy nhất 1 nhóm menu tại một thời điểm (-1 = đóng tất cả)
  final expandedGroupIndex = 0.obs;

  @override
  void onInit() {
    super.onInit();
    _ensureWorkspaceCached();
  }

  // Tự động kiểm tra tính hợp lệ của token khi khởi động Dashboard.
  Future<void> _ensureWorkspaceCached() async {
    final me = await _authService.getMe();
    if (me == null) {
      debugPrint('DashboardController: Token hết hạn hoặc không hợp lệ -> Tự động chuyển về màn Đăng nhập');
      await _authService.logout();
      Get.offAllNamed(AppRoutes.login);
      return;
    }

    if (Get.isRegistered<ChatController>()) {
      Get.find<ChatController>().loadModels();
    }
  }

  void changePage(int index, int groupIndex) {
    currentIndex.value = index;
    expandedGroupIndex.value = groupIndex;
  }

  void toggleGroup(int groupIndex) {
    if (expandedGroupIndex.value == groupIndex) {
      expandedGroupIndex.value = -1; // Thu gọn nếu bấm lại đúng nhóm đang mở
    } else {
      expandedGroupIndex.value = groupIndex; // Mở nhóm mới và tự động đóng các nhóm khác (Accordion)
    }
  }

  Future<void> logout() async {
    await _authService.logout();
    Get.offAllNamed(AppRoutes.login);
  }
}
