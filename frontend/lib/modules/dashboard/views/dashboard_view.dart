import 'package:flutter/material.dart';
import 'package:get/get.dart';
import '../../../core/routing/module_routes.dart';
import '../../../core/shell/app_shell.dart';
import '../controllers/dashboard_controller.dart';
import 'widgets/dashboard_content_body.dart';

/// Task 9 — trước đây `DashboardView` tự lắp ráp toàn bộ chrome (sidebar,
/// topbar, floating voice, `RuntimeAppChrome`) NGAY TẠI ĐÂY. Chrome đó nay
/// thuộc về `AppShell` — dùng chung cho MỌI route module, không riêng gì
/// `/hub`. `DashboardView` giờ chỉ còn là "nội dung hub": danh sách sidebar
/// cũ (`DashboardContentBody`) cho các mục CHƯA có route canonical riêng.
class DashboardView extends GetView<DashboardController> {
  const DashboardView({super.key});

  @override
  Widget build(BuildContext context) {
    return AppShell(
      activeModule: WorkspaceModule.hub,
      child: DashboardContentBody(controller: controller),
    );
  }
}
