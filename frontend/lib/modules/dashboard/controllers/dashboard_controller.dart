import 'package:flutter/foundation.dart';
import 'package:get/get.dart';
import '../../../modules/auth/services/auth_service.dart';
import '../../../core/routing/app_routes.dart';
import '../../../data/models/stage_model.dart';
import 'package:shared_preferences/shared_preferences.dart';

class DashboardController extends GetxController {
  final AuthService _authService = AuthService();

  // Selected tab index
  final currentIndex = 0.obs;
  final strategyInitialTabIndex = 0.obs;

  // Stage-Aware Adaptive Sidebar & Demo Mode
  final selectedStage = ProjectStage.s2SolutionValidation.obs;
  final isStageFilteringEnabled = true.obs;
  final isDemoModeActive = true.obs;

  // Accordion mode: chỉ mở duy nhất 1 nhóm menu tại một thời điểm (-1 = đóng tất cả)
  final expandedGroupIndex = 0.obs;
  final developerMode = false.obs;

  @override
  void onInit() {
    super.onInit();
    _ensureWorkspaceCached();
    _loadDeveloperMode();
  }

  void setDemoStage(ProjectStage stage) {
    selectedStage.value = stage;
  }

  void toggleStageFiltering() {
    isStageFilteringEnabled.value = !isStageFilteringEnabled.value;
  }

  Future<void> _loadDeveloperMode() async {
    final preferences = await SharedPreferences.getInstance();
    developerMode.value = preferences.getBool('developer_mode') ??
        preferences.getBool('v13_developer_mode') ??
        false;
  }

  Future<void> setDeveloperMode(bool enabled) async {
    developerMode.value = enabled;
    await (await SharedPreferences.getInstance()).setBool('developer_mode', enabled);
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
  }

  void changePage(int index, int groupIndex, [int strategySubTab = 0]) {
    currentIndex.value = index;
    expandedGroupIndex.value = groupIndex;
    strategyInitialTabIndex.value = strategySubTab;
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
