import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../../../../core/routing/module_routes.dart';
import '../../../../core/services/feature_flags_controller.dart';
import '../../../../core/theme/app_theme.dart';
import '../../../../shared/widgets/feature_not_enabled_view.dart';
import '../../../hologram_hub/views/hologram_hub_view.dart';
import '../../controllers/dashboard_controller.dart';
import '../../models/dashboard_nav_config.dart';

/// Task 9 — trước đây widget này là "authority" DUY NHẤT chọn view bằng một
/// index nguyên (switch 0..33), không thể deep-link/back-stack/guard riêng
/// từng mục. Nay chỉ còn giữ các mục CHƯA có route canonical
/// (`WorkspaceModule`) — xem `module_routes.dart`. Mục ĐÃ migrate không còn
/// build view tại đây nữa: `_buildFeatureView` trở thành một "redirect
/// adapter" tạm thời, điều hướng sang route thật thay vì render inline.
///
/// Switch giờ chỉ còn case 0 (hub) — mọi module khác đã có route canonical
/// riêng, redirect adapter phía trên (`moduleForLegacyIndex`) xử lý hết. Toàn
/// bộ switch này (và `DashboardContentBody`) sẽ được xoá hẳn cùng lúc ở
/// Task 6.
class DashboardContentBody extends StatelessWidget {
  final DashboardController controller;

  const DashboardContentBody({super.key, required this.controller});

  @override
  Widget build(BuildContext context) {
    return Obx(() {
      final index = controller.currentIndex.value;
      final item = DashboardNavConfig.allNavItems.firstWhereOrNull((candidate) => candidate.index == index);
      if (item?.flagKey != null && !Get.find<FeatureFlagsController>().isEnabled(item!.flagKey!)) {
        return FeatureNotEnabledView(featureName: item.label);
      }
      try {
        return _buildFeatureView(index);
      } catch (e) {
        return _errorView(e.toString());
      }
    });
  }

  Widget _buildFeatureView(int index) {
    // Redirect adapter: mục này đã có route canonical thật — điều hướng
    // sang đó thay vì render trực tiếp. Không dùng cho `index == 0` (hub) vì
    // hub CHÍNH LÀ route đang host widget này.
    final module = moduleForLegacyIndex(index);
    if (module != null) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (Get.currentRoute != module.path) {
          Get.toNamed(module.path);
        }
        // SỬA LỖI review vòng 2 (biến thể thứ hai của Critical #1) —
        // `currentIndex` là state DÙNG CHUNG (`DashboardController` là
        // singleton `permanent`), và không chỉ sidebar mới ghi vào nó:
        // `hub_command_mixin.dart`'s `openDashboard()` (Settings icon trên
        // Hub, `openStrategyNextActions`, ...) cũng gọi `changePage()` với 1
        // index đã migrate rồi mới điều hướng — để lại `currentIndex` "dính"
        // ở giá trị migrate đó. Lần sau `/hub` build lại (vd. sau khi back
        // từ chính route vừa push) mà không có gì reset `currentIndex`, `Obx`
        // này đọc lại đúng index migrate cũ → tự động push lại route đó →
        // lặp vô hạn mỗi lần back — HỆT bug đã sửa ở `AppShell`, chỉ khác nơi
        // ghi vào `currentIndex`.
        //
        // Sửa tại ĐÚNG MỘT điểm trung tâm này (thay vì lần theo từng nơi ghi
        // `currentIndex`, vốn có thể còn nơi khác chưa phát hiện): ngay sau
        // khi kích hoạt điều hướng, reset `currentIndex` về sentinel hub (0)
        // — bất kể AI đã ghi giá trị migrate vào đó, giá trị "dính" không
        // bao giờ còn tồn tại để redirect adapter đọc lại ở lần build sau.
        controller.currentIndex.value = 0;
      });
      return const Center(child: CircularProgressIndicator());
    }

    switch (index) {
      case 0:
        return const HologramHubView();
      default:
        return const HologramHubView();
    }
  }

  Widget _errorView(String error) => Center(
        child: Padding(
          padding: const EdgeInsets.all(24.0),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              const Icon(Icons.error_outline, color: AppTheme.error, size: 48),
              const SizedBox(height: 16),
              Text(
                'Không thể tải tính năng:\n$error',
                textAlign: TextAlign.center,
                style: const TextStyle(color: AppTheme.error, fontSize: 14),
              ),
            ],
          ),
        ),
      );
}
