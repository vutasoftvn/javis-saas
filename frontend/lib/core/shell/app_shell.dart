// Task 9 — Chrome DUY NHẤT cho mọi module workspace: sidebar/topbar/floating
// voice/banner. Nội dung nghiệp vụ (`child`) do CHÍNH route của module đó sở
// hữu (binding + page riêng, xem `module_routes.dart`) — `AppShell` không
// biết và không cần biết nội dung bên trong là gì, chỉ lo phần khung.
//
// Layering (đọc kỹ trước khi sửa — sai thứ tự dễ gây double-banner):
//   AppShell → RuntimeAppChrome (Task 5, banner PHẢI phủ toàn bộ shell kể cả
//   sidebar) → Scaffold (sidebar desktop / drawer mobile) → child.
//
// Lịch sử: `AppShell` từng phải né một bug redirect-loop khi ghi đè
// `dashboardController.currentIndex` — bug đó gắn với `DashboardContentBody`
// tại `/hub`, widget đã bị XOÁ HẲN ở Task 6 (hub-no-sidebar; `/hub` nay luôn
// là `HologramHubView` trực tiếp). `AppShell` không còn đụng tới
// `currentIndex`/`expandedGroupIndex`; highlight sidebar cho route module suy
// ra tại chỗ trong `dashboard_sidebar.dart` từ `Get.currentRoute`.
import 'package:flutter/material.dart';
import 'package:get/get.dart';

import '../../modules/dashboard/views/widgets/dashboard_sidebar.dart';
import '../../modules/dashboard/views/widgets/dashboard_top_bar.dart';
import '../../modules/dashboard/views/widgets/floating_voice_hologram.dart';
import '../routing/module_routes.dart';
import '../theme/app_theme.dart';
import '../widgets/runtime_app_chrome.dart';
import 'app_shell_controller.dart';

class AppShell extends StatelessWidget {
  const AppShell({super.key, required this.child, this.activeModule});

  /// Nội dung module hiện tại — view nghiệp vụ hiện có, KHÔNG bị viết lại.
  final Widget child;

  /// Module đang active — hiện chỉ dùng để giữ thông tin ngữ nghĩa cho các
  /// route module (tương lai nếu chrome cần biết module nào đang mở). Sau
  /// fix Critical #1, `AppShell` KHÔNG dùng giá trị này để ghi vào
  /// `DashboardController` nữa — xem `dashboard_sidebar.dart` cho cách
  /// highlight route module được suy ra không-mutate.
  final WorkspaceModule? activeModule;

  @override
  Widget build(BuildContext context) {
    AppShellController.ensureShellDependencies();
    final dashboardController = Get.find<AppShellController>().dashboardController;

    final bool isDesktop = MediaQuery.of(context).size.width >= 800;

    if (isDesktop) {
      return RuntimeAppChrome(
        child: Scaffold(
          body: Container(
            decoration: const BoxDecoration(
              gradient: AppTheme.backgroundLinearGradient,
            ),
            child: Stack(
              children: [
                Padding(
                  padding: const EdgeInsets.all(12.0),
                  child: Row(
                    children: [
                      DashboardDesktopSidebar(controller: dashboardController),
                      const SizedBox(width: 12),
                      Expanded(child: child),
                    ],
                  ),
                ),
                const FloatingVoiceHologram(),
              ],
            ),
          ),
        ),
      );
    }

    final GlobalKey<ScaffoldState> scaffoldKey = GlobalKey<ScaffoldState>();
    return RuntimeAppChrome(
      child: Scaffold(
        key: scaffoldKey,
        drawer: DashboardMobileDrawer(controller: dashboardController),
        appBar: DashboardMobileAppBar(
          scaffoldKey: scaffoldKey,
          controller: dashboardController,
        ),
        body: Stack(
          children: [
            Container(
              decoration: const BoxDecoration(
                gradient: AppTheme.backgroundLinearGradient,
              ),
              child: child,
            ),
            const FloatingVoiceHologram(),
          ],
        ),
      ),
    );
  }
}
