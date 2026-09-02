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
//
// SỬA LỖI review (Critical #1) — bản trước ghi `dashboardController
// .currentIndex.value = legacyIndex` mỗi lần build cho 1 module đã migrate.
// `DashboardController` là singleton `permanent` DÙNG CHUNG với
// `DashboardContentBody` tại `/hub` (route đó KHÔNG bị dispose khi bị đẩy
// xuống dưới route module vừa push — Flutter giữ nguyên state). Ghi đè
// `currentIndex` như vậy làm `/hub` "nhớ nhầm" nó đang ở tab của module vừa
// rời đi; quay lại `/hub` bằng back, `DashboardContentBody` đọc thấy
// `currentIndex` khớp module đó nhưng `Get.currentRoute` lại là `/hub` →
// redirect adapter của nó (`dashboard_content_body.dart`) hiểu nhầm là
// "chưa điều hướng xong" và tự động `Get.toNamed` lại chính route vừa thoát
// — lặp vô hạn khi bấm back nhiều lần.
//
// Gốc rễ: `currentIndex` phục vụ HAI mục đích xung đột (nội dung tab tại chỗ
// trên `/hub`, VÀ đồng bộ highlight sidebar cho route module). `AppShell`
// nay KHÔNG còn ghi vào `currentIndex`/`expandedGroupIndex` nữa — chỉ đọc.
// Highlight đúng cho route module (khi vào thẳng qua deep-link) được suy ra
// tại chỗ trong `dashboard_sidebar.dart` từ `Get.currentRoute`, không qua
// mutate state dùng chung.
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
