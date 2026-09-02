// Task 9 — Chrome DUY NHẤT cho mọi module workspace: sidebar/topbar/floating
// voice/banner. Nội dung nghiệp vụ (`child`) do CHÍNH route của module đó sở
// hữu (binding + page riêng, xem `module_routes.dart`) — `AppShell` không
// biết và không cần biết nội dung bên trong là gì, chỉ lo phần khung.
//
// Layering (đọc kỹ trước khi sửa — sai thứ tự dễ gây double-banner):
//   AppShell → RuntimeAppChrome (Task 5, banner PHẢI phủ toàn bộ shell kể cả
//   sidebar) → Scaffold (sidebar desktop / drawer mobile) → child.
// Đây là cấu trúc y hệt `DashboardView` cũ trước Task 9 — chỉ chuyển quyền
// sở hữu sang một widget dùng chung cho mọi route, không đổi cách lồng.
import 'package:flutter/material.dart';
import 'package:get/get.dart';

import '../../modules/dashboard/models/dashboard_nav_config.dart';
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

  /// Module đang active, dùng để đồng bộ highlight sidebar khi vào thẳng
  /// route canonical (vd. deep-link `/work/tasks`) mà không qua tap sidebar.
  /// Null nghĩa là chrome đang host nội dung không thuộc danh sách module đã
  /// migrate (vd. hub đang hiển thị một mục sidebar cũ qua
  /// `DashboardContentBody`) — khi đó không ép lại `currentIndex`.
  final WorkspaceModule? activeModule;

  /// Tìm group chứa [legacyIndex] trong `DashboardNavConfig.coreNavGroups` —
  /// dùng vị trí trong danh sách NGUỒN (ổn định), không dùng danh sách đã lọc
  /// theo feature flag của `_getVisibleNavGroups()` (danh sách đó có thể bớt
  /// item nhưng không rút gọn số group, vì không group nào rỗng hoàn toàn
  /// chỉ vì ẩn 1 item — an toàn để tra cứu index nhóm ổn định ở đây).
  static int? _groupIndexForLegacyIndex(int legacyIndex) {
    final groups = DashboardNavConfig.coreNavGroups;
    for (var i = 0; i < groups.length; i++) {
      if (groups[i].items.any((item) => item.index == legacyIndex)) return i;
    }
    return null;
  }

  @override
  Widget build(BuildContext context) {
    AppShellController.ensureShellDependencies();
    final dashboardController = Get.find<AppShellController>().dashboardController;

    final module = activeModule;
    final legacyIndex = module == null
        ? null
        : (module == WorkspaceModule.hub ? 0 : legacyDashboardIndexForModule[module]);
    if (legacyIndex != null) {
      // Đồng bộ SAU frame hiện tại — tránh mutate Rx trong lúc build.
      WidgetsBinding.instance.addPostFrameCallback((_) {
        dashboardController.currentIndex.value = legacyIndex;
        final groupIndex = _groupIndexForLegacyIndex(legacyIndex);
        if (groupIndex != null) {
          dashboardController.expandedGroupIndex.value = groupIndex;
        }
      });
    }

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
