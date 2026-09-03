// Task 9 — controller CHUNG cho chrome (sidebar/topbar/banner/floating
// voice), tách khỏi state/network của từng module nghiệp vụ. Trước đây mọi
// route dashboard đều gánh `DashboardBinding` eager-load TOÀN BỘ controller
// của mọi module (kể cả module không hề được mở) — Task 9 Step 3 thu hẹp lại
// còn dependency thuộc về SHELL: `DashboardController` (state sidebar: index
// đang chọn, group mở, dev mode, demo stage) vẫn được tái sử dụng làm nguồn
// state cho `DashboardDesktopSidebar`/`DashboardMobileDrawer` hiện có — KHÔNG
// viết lại 2 widget đó (ngoài phạm vi Task 9), chỉ đảm bảo chúng luôn có
// đúng 1 instance dùng chung dù vào module nào.
import 'package:get/get.dart';

import '../../modules/dashboard/controllers/dashboard_controller.dart';
import '../../modules/hologram_hub/controllers/founder_command_center_controller.dart';
import '../../modules/hologram_hub/controllers/hologram_hub_controller.dart';
import '../services/feature_flags_controller.dart';
import 'chat_panel_controller.dart';

class AppShellController extends GetxController {
  /// Đăng ký (nếu chưa có) các dependency thuộc về CHROME — không thuộc bất
  /// kỳ module nghiệp vụ cụ thể nào — để MỌI route module (mỗi route giờ có
  /// binding riêng, không còn `DashboardBinding` gánh hết) vẫn có đủ state
  /// cho sidebar/topbar/floating voice hoạt động đúng.
  ///
  /// `HologramHubController`/`FounderCommandCenterController` cũng thuộc về
  /// đây (không phải feature riêng của module nào): `FloatingVoiceHologram` —
  /// hiển thị trên MỌI route qua `AppShell` — đọc trực tiếp
  /// `HologramHubController` (xem `floating_voice_hologram.dart`). Trước
  /// Task 9, controller này luôn có sẵn vì mọi route đều đi qua
  /// `DashboardBinding`/`HologramHubBinding`; nay các route module có binding
  /// riêng không còn tự đăng ký nó — thiếu bước này sẽ khiến floating voice
  /// lỗi "improper use of GetX" trên mọi route KHÔNG PHẢI `/hub`.
  static void ensureShellDependencies() {
    if (!Get.isRegistered<FeatureFlagsController>()) {
      Get.put<FeatureFlagsController>(FeatureFlagsController(), permanent: true);
    }
    if (!Get.isRegistered<DashboardController>()) {
      Get.put<DashboardController>(DashboardController(), permanent: true);
    }
    if (!Get.isRegistered<HologramHubController>()) {
      Get.put<HologramHubController>(HologramHubController(), permanent: true);
    }
    if (!Get.isRegistered<FounderCommandCenterController>()) {
      Get.put<FounderCommandCenterController>(FounderCommandCenterController(), permanent: true);
    }
    if (!Get.isRegistered<ChatPanelController>()) {
      Get.put<ChatPanelController>(ChatPanelController(), permanent: true);
    }
    if (!Get.isRegistered<AppShellController>()) {
      Get.put<AppShellController>(AppShellController(), permanent: true);
    }
  }

  DashboardController get dashboardController => Get.find<DashboardController>();
}
